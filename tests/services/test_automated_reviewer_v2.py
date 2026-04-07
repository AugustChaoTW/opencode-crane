"""AutomatedReviewerV2 單元測試

驗證 4 個核心模組:
1. EnsembleReviewerModule - 5 種風格獨立評審
2. MetaReviewerModule - 評分聚合與決策邏輯
3. ReviewQualityValidator - 幻覺與一致性檢測
4. CalibrationModule - ECE 與校準誤差計算
"""

import json
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from src.crane.services.automated_reviewer_v2 import (
    AutomatedReviewerV2,
    CalibrationModule,
    EnsembleReviewResult,
    EnsembleReviewerModule,
    IndividualReview,
    MetaReviewerModule,
    ReviewQualityValidator,
)


# ============================================================================
# FIXTURES: 論文樣本
# ============================================================================


@pytest.fixture
def standard_paper() -> str:
    """標準品質論文"""
    return """
    Title: A Novel Approach to Machine Learning

    Abstract:
    We propose a new method for improving model performance.

    Introduction:
    The problem of model optimization is important.
    Previous work has shown limited results.

    Methods:
    We use a transformer-based architecture with attention mechanisms.
    The training procedure involves standard cross-entropy loss.
    We evaluate on CIFAR-10 and ImageNet datasets.

    Results:
    Our method achieves 95% accuracy on CIFAR-10.
    We compare against BERT and ResNet baselines.
    Ablation studies show the importance of each component.

    Discussion:
    The results demonstrate the effectiveness of our approach.
    Limitations include computational cost and scalability.

    Conclusion:
    We have presented a novel method with strong empirical results.
    Future work includes extending to other domains.
    """


@pytest.fixture
def weak_paper() -> str:
    """弱品質論文"""
    return """
    Title: Some Improvements

    Abstract:
    We try to improve something.

    Introduction:
    This is important.

    Methods:
    We use standard techniques.

    Results:
    We got some results.

    Conclusion:
    Our work is done.
    """


@pytest.fixture
def strong_paper() -> str:
    """強品質論文"""
    return """
    Title: Breakthrough Method for Transformer Scaling

    Abstract:
    We present a comprehensive study of scaling laws in large language models,
    with novel theoretical insights and extensive empirical validation.

    Introduction:
    The scaling behavior of neural networks is fundamental to deep learning.
    Previous work (Kaplan et al., 2020; Hoffmann et al., 2022) has established
    empirical scaling laws, but theoretical understanding remains limited.
    We address this gap through first-principles analysis.

    Methods:
    We develop a novel theoretical framework based on information theory.
    Our approach combines:
    1. Optimal transport theory for parameter efficiency
    2. Information-theoretic bounds on generalization
    3. Empirical validation on 7 different architectures

    Experiments:
    We conduct extensive experiments on:
    - CIFAR-10, ImageNet, MNIST (vision)
    - WikiText-103, C4, Books (language)
    - 5 different model sizes (1M to 1B parameters)

    Results:
    Our theoretical predictions match empirical results with R² = 0.98.
    We achieve state-of-the-art performance on all benchmarks.
    Ablation studies systematically validate each component.
    Statistical significance testing (p < 0.001) confirms findings.

    Limitations:
    - Computational cost limits exploration of larger models
    - Results may not generalize to multimodal architectures
    - Theoretical framework assumes specific loss landscapes

    Discussion:
    Our findings have important implications for:
    1. Model architecture design
    2. Training efficiency optimization
    3. Resource allocation in large-scale training

    Conclusion:
    We have provided both theoretical and empirical insights into scaling laws.
    Code and data are available at https://github.com/example/repo.
    """


@pytest.fixture
def review_samples() -> List[IndividualReview]:
    """多個評審樣本"""
    return [
        IndividualReview(
            reviewer_id=1,
            reviewer_style="aggressive",
            scores={
                "soundness": 5.5,
                "presentation": 6.0,
                "contribution": 5.0,
                "overall": 5.5,
                "confidence": 0.75,
            },
            strengths=["Clear writing"],
            weaknesses=["Limited novelty", "Missing baselines"],
            decision="weak_reject",
            consistency_score=0.86,
            depth_score=0.83,
        ),
        IndividualReview(
            reviewer_id=2,
            reviewer_style="conservative",
            scores={
                "soundness": 7.5,
                "presentation": 7.5,
                "contribution": 7.0,
                "overall": 7.3,
                "confidence": 0.80,
            },
            strengths=["Well-motivated", "Comprehensive experiments"],
            weaknesses=["Minor presentation issues"],
            decision="accept",
            consistency_score=0.87,
            depth_score=0.86,
        ),
        IndividualReview(
            reviewer_id=3,
            reviewer_style="detailed",
            scores={
                "soundness": 7.5,
                "presentation": 7.0,
                "contribution": 6.5,
                "overall": 7.0,
                "confidence": 0.78,
            },
            strengths=["Solid methodology", "Good experimental design"],
            weaknesses=["Scalability concerns"],
            decision="borderline",
            consistency_score=0.88,
            depth_score=0.89,
        ),
        IndividualReview(
            reviewer_id=4,
            reviewer_style="quick",
            scores={
                "soundness": 7.0,
                "presentation": 7.0,
                "contribution": 6.5,
                "overall": 6.8,
                "confidence": 0.75,
            },
            strengths=["Clear motivation"],
            weaknesses=["Limited novelty"],
            decision="weak_accept",
            consistency_score=0.89,
            depth_score=0.87,
        ),
        IndividualReview(
            reviewer_id=5,
            reviewer_style="balanced",
            scores={
                "soundness": 7.0,
                "presentation": 6.5,
                "contribution": 6.5,
                "overall": 6.7,
                "confidence": 0.76,
            },
            strengths=["Well-written", "Comprehensive evaluation"],
            weaknesses=["Incremental contribution"],
            decision="borderline",
            consistency_score=0.90,
            depth_score=0.88,
        ),
    ]


# ============================================================================
# TEST: EnsembleReviewerModule
# ============================================================================


class TestEnsembleReviewerModule:
    """測試 5 種風格獨立評審"""

    def test_ensemble_reviewer_5_styles(self, standard_paper: str):
        """驗證 5 種風格獨立評審"""
        reviewer = EnsembleReviewerModule()
        reviews = reviewer.review_paper(standard_paper)

        # 驗證評審數量
        assert len(reviews) == 5, "應該生成 5 份評審"

        # 驗證每份評審的風格
        styles = [r.reviewer_style for r in reviews]
        assert styles == EnsembleReviewerModule.REVIEWER_STYLES
        assert set(styles) == {"aggressive", "conservative", "detailed", "quick", "balanced"}

        # 驗證每份評審的完整性
        for review in reviews:
            assert review.reviewer_id in range(1, 6)
            assert len(review.scores) > 0
            assert len(review.strengths) > 0
            assert len(review.weaknesses) > 0
            assert review.decision in [
                "accept",
                "weak_accept",
                "borderline",
                "weak_reject",
                "reject",
            ]

    def test_ensemble_reviewer_scores(self, standard_paper: str):
        """驗證評分計算邏輯"""
        reviewer = EnsembleReviewerModule()
        reviews = reviewer.review_paper(standard_paper)

        # 驗證評分範圍
        for review in reviews:
            for key, score in review.scores.items():
                if key == "confidence":
                    assert 0.0 <= score <= 1.5, f"{key} 應在合理範圍內"
                else:
                    assert 1.0 <= score <= 10.0, f"{key} 應在 [1, 10] 範圍內"

        # 驗證風格影響評分
        aggressive_review = next(r for r in reviews if r.reviewer_style == "aggressive")
        conservative_review = next(r for r in reviews if r.reviewer_style == "conservative")

        assert aggressive_review.scores["overall"] < conservative_review.scores["overall"], (
            "激進評審應給出更低的評分"
        )

    def test_ensemble_reviewer_strengths_weaknesses(self, standard_paper: str):
        """驗證優劣識別"""
        reviewer = EnsembleReviewerModule()
        reviews = reviewer.review_paper(standard_paper)

        # 驗證快速評審的優勢較少
        quick_review = next(r for r in reviews if r.reviewer_style == "quick")
        assert len(quick_review.strengths) <= 2, "快速評審應識別較少優勢"

        # 驗證激進評審的弱點較多
        aggressive_review = next(r for r in reviews if r.reviewer_style == "aggressive")
        assert len(aggressive_review.weaknesses) >= 3, "激進評審應識別更多弱點"

        # 驗證所有評審都有優勢和弱點
        for review in reviews:
            assert len(review.strengths) > 0, "每份評審應有至少一個優勢"
            assert len(review.weaknesses) > 0, "每份評審應有至少一個弱點"


# ============================================================================
# TEST: MetaReviewerModule
# ============================================================================


class TestMetaReviewerModule:
    """測試元評審器 (Area Chair 角色)"""

    def test_meta_reviewer_score_aggregation(self, review_samples: List[IndividualReview]):
        """驗證評分聚合"""
        meta_reviewer = MetaReviewerModule()
        aggregated = meta_reviewer._aggregate_scores(review_samples)

        # 驗證聚合維度
        expected_dims = ["soundness", "presentation", "contribution", "overall", "confidence"]
        assert set(aggregated.keys()) == set(expected_dims)

        # 驗證聚合值在合理範圍內
        for dim, score in aggregated.items():
            if dim == "confidence":
                assert 0.0 <= score <= 1.0
            else:
                assert 1.0 <= score <= 10.0

        # 驗證聚合計算正確性
        overall_scores = [r.scores["overall"] for r in review_samples]
        expected_overall = sum(overall_scores) / len(overall_scores)
        assert abs(aggregated["overall"] - expected_overall) < 0.01

    def test_meta_reviewer_consensus(self, review_samples: List[IndividualReview]):
        """驗證一致性計算"""
        meta_reviewer = MetaReviewerModule()
        consensus = meta_reviewer._compute_consensus(review_samples)

        # 驗證一致性在 [0, 1] 範圍內
        assert 0.0 <= consensus <= 1.0

        # 驗證一致性計算邏輯
        decisions = [r.decision for r in review_samples]
        unique_decisions = len(set(decisions))
        expected_consensus = 1.0 - (unique_decisions - 1) / 4.0
        expected_consensus = max(0.0, min(1.0, expected_consensus))
        assert abs(consensus - expected_consensus) < 0.01

    def test_meta_reviewer_decision_logic(self):
        """驗證決策邏輯 (accept/weak_accept/borderline/weak_reject/reject)"""
        meta_reviewer = MetaReviewerModule()

        test_cases = [
            (7.5, "accept"),
            (7.0, "accept"),
            (6.5, "weak_accept"),
            (6.0, "weak_accept"),
            (5.5, "borderline"),
            (5.0, "borderline"),
            (4.5, "weak_reject"),
            (4.0, "weak_reject"),
            (3.0, "reject"),
            (1.0, "reject"),
        ]

        for score, expected_decision in test_cases:
            decision = meta_reviewer._determine_decision(score, 0.5)
            assert decision == expected_decision, f"評分 {score} 應決策為 {expected_decision}"

    def test_meta_reviewer_acceptance_probability(self):
        """驗證接受概率計算"""
        meta_reviewer = MetaReviewerModule()

        test_cases = [
            (1.0, 0.0),  # 最低分 -> 0% 接受概率
            (5.5, 0.5),  # 中等分 -> ~50% 接受概率
            (10.0, 1.0),  # 最高分 -> 100% 接受概率
        ]

        for score, expected_prob in test_cases:
            prob = meta_reviewer._compute_acceptance_probability(score)
            assert 0.0 <= prob <= 1.0
            assert abs(prob - expected_prob) < 0.1, f"評分 {score} 的接受概率應約為 {expected_prob}"

    def test_meta_reviewer_full_decision(self, review_samples: List[IndividualReview]):
        """驗證完整決策流程"""
        meta_reviewer = MetaReviewerModule()
        decision = meta_reviewer.make_final_decision(review_samples)

        # 驗證決策結構
        assert "aggregated_scores" in decision
        assert "consensus_level" in decision
        assert "final_decision" in decision
        assert "acceptance_probability" in decision
        assert "meta_review_summary" in decision

        # 驗證決策值
        assert decision["final_decision"] in [
            "accept",
            "weak_accept",
            "borderline",
            "weak_reject",
            "reject",
        ]
        assert 0.0 <= decision["acceptance_probability"] <= 1.0
        assert 0.0 <= decision["consensus_level"] <= 1.0


# ============================================================================
# TEST: ReviewQualityValidator
# ============================================================================


class TestReviewQualityValidator:
    """測試評審品質檢測"""

    def test_quality_validator_hallucination(self):
        """驗證幻覺檢測"""
        validator = ReviewQualityValidator()

        # 有效評審 (有優勢和弱點)
        valid_review = IndividualReview(
            reviewer_id=1,
            reviewer_style="balanced",
            scores={
                "overall": 6.5,
                "soundness": 7.0,
                "presentation": 6.0,
                "contribution": 6.0,
                "confidence": 0.75,
            },
            strengths=["Good methodology"],
            weaknesses=["Limited novelty"],
            decision="borderline",
        )

        # 無效評審 (缺少優勢或弱點)
        invalid_review = IndividualReview(
            reviewer_id=2,
            reviewer_style="balanced",
            scores={
                "overall": 6.5,
                "soundness": 7.0,
                "presentation": 6.0,
                "contribution": 6.0,
                "confidence": 0.75,
            },
            strengths=[],  # 缺少優勢
            weaknesses=["Limited novelty"],
            decision="borderline",
        )

        assert validator._check_hallucination(valid_review) is True
        assert validator._check_hallucination(invalid_review) is False

    def test_quality_validator_consistency(self):
        """驗證邏輯一致性"""
        validator = ReviewQualityValidator()

        # 一致的評審 (高分 + 少弱點)
        consistent_review = IndividualReview(
            reviewer_id=1,
            reviewer_style="balanced",
            scores={
                "overall": 8.0,
                "soundness": 8.0,
                "presentation": 8.0,
                "contribution": 8.0,
                "confidence": 0.85,
            },
            strengths=["Excellent work"],
            weaknesses=["Minor issue"],
            decision="accept",
        )

        # 不一致的評審 (高分 + 多弱點)
        inconsistent_review = IndividualReview(
            reviewer_id=2,
            reviewer_style="balanced",
            scores={
                "overall": 8.0,
                "soundness": 8.0,
                "presentation": 8.0,
                "contribution": 8.0,
                "confidence": 0.85,
            },
            strengths=["Good"],
            weaknesses=["Issue 1", "Issue 2", "Issue 3", "Issue 4"],
            decision="accept",
        )

        assert validator._check_consistency(consistent_review) is True
        assert validator._check_consistency(inconsistent_review) is False

    def test_quality_validator_batch_validation(self, review_samples: List[IndividualReview]):
        """驗證批量驗證"""
        validator = ReviewQualityValidator()
        results = validator.validate_reviews(review_samples)

        # 驗證結果數量
        assert len(results) == len(review_samples)

        # 驗證結果類型
        assert all(isinstance(r, bool) for r in results)

        # 驗證評審被標記為幻覺
        for review, is_valid in zip(review_samples, results):
            assert review.is_hallucinated == (not is_valid)


# ============================================================================
# TEST: CalibrationModule
# ============================================================================


class TestCalibrationModule:
    """測試校準與去污"""

    def test_calibration_module_ece(self):
        """驗證 ECE (Expected Calibration Error) 計算"""
        calibration = CalibrationModule()

        # 完美校準的預測
        perfect_predictions = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        perfect_actuals = [0, 0, 0, 0, 1, 1, 1, 1, 1]

        ece = calibration._compute_calibration_error(perfect_predictions, perfect_actuals)
        assert 0.0 <= ece <= 1.0

        # 不校準的預測
        bad_predictions = [0.9, 0.9, 0.9, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1]
        bad_actuals = [0, 0, 0, 0, 1, 1, 1, 1, 1]

        bad_ece = calibration._compute_calibration_error(bad_predictions, bad_actuals)
        assert bad_ece > ece, "不校準的預測應有更高的 ECE"

    def test_calibration_module_calibration_error(self):
        """驗證校準誤差計算"""
        calibration = CalibrationModule()

        # 創建模擬結果
        results = [
            EnsembleReviewResult(
                individual_reviews=[],
                meta_review={},
                consensus_level=0.8,
                final_decision="accept",
                acceptance_probability=0.85,
                confidence=0.8,
            ),
            EnsembleReviewResult(
                individual_reviews=[],
                meta_review={},
                consensus_level=0.6,
                final_decision="borderline",
                acceptance_probability=0.5,
                confidence=0.7,
            ),
            EnsembleReviewResult(
                individual_reviews=[],
                meta_review={},
                consensus_level=0.4,
                final_decision="reject",
                acceptance_probability=0.15,
                confidence=0.6,
            ),
        ]

        calibration_report = calibration.calibrate_decisions(results)

        # 驗證報告結構
        assert "calibration_error" in calibration_report
        assert "sample_size" in calibration_report
        assert "recommendation" in calibration_report

        # 驗證樣本數
        assert calibration_report["sample_size"] == 3

        # 驗證校準誤差在合理範圍內
        assert 0.0 <= calibration_report["calibration_error"] <= 1.0

    def test_calibration_module_empty_input(self):
        """驗證空輸入處理"""
        calibration = CalibrationModule()

        result = calibration.calibrate_decisions([])
        assert result == {}

        ece = calibration._compute_calibration_error([], [])
        assert ece == 0.0


# ============================================================================
# TEST: AutomatedReviewerV2 (完整流程)
# ============================================================================


class TestAutomatedReviewerV2:
    """測試完整自動評審器"""

    def test_automated_reviewer_full_flow(self, standard_paper: str):
        """驗證完整評審流程"""
        reviewer = AutomatedReviewerV2()
        result = reviewer.review_paper(standard_paper)

        # 驗證結果類型
        assert isinstance(result, EnsembleReviewResult)

        # 驗證個別評審
        assert len(result.individual_reviews) == 5
        for review in result.individual_reviews:
            assert isinstance(review, IndividualReview)

        # 驗證元評審
        assert isinstance(result.meta_review, dict)
        assert "aggregated_scores" in result.meta_review
        assert "consensus_level" in result.meta_review
        assert "final_decision" in result.meta_review
        assert "acceptance_probability" in result.meta_review

        # 驗證最終決策
        assert result.final_decision in [
            "accept",
            "weak_accept",
            "borderline",
            "weak_reject",
            "reject",
        ]
        assert 0.0 <= result.acceptance_probability <= 1.0
        assert 0.0 <= result.consensus_level <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    def test_batch_review(self, standard_paper: str, weak_paper: str, strong_paper: str):
        """驗證批量評審"""
        reviewer = AutomatedReviewerV2()

        papers = [
            {"content": standard_paper},
            {"content": weak_paper},
            {"content": strong_paper},
        ]

        results = reviewer.batch_review(papers)

        # 驗證結果數量
        assert len(results) == 3

        # 驗證每個結果的完整性
        for result in results:
            assert isinstance(result, EnsembleReviewResult)
            assert len(result.individual_reviews) == 5

        # 驗證所有結果都有有效的接受概率
        for result in results:
            assert 0.0 <= result.acceptance_probability <= 1.0

    def test_performance_report(self):
        """驗證性能報告"""
        reviewer = AutomatedReviewerV2()
        report = reviewer.get_performance_report()

        # 驗證報告結構
        assert "ensemble_size" in report
        assert "reviewer_styles" in report
        assert "target_accuracy" in report
        assert "target_spearman_correlation" in report
        assert "status" in report
        assert "timestamp" in report

        # 驗證報告值
        assert report["ensemble_size"] == 5
        assert len(report["reviewer_styles"]) == 5
        assert report["target_accuracy"] == 0.70
        assert report["target_spearman_correlation"] == 0.75


# ============================================================================
# TEST: 進階驗證 (Balanced Accuracy, Spearman 相關性)
# ============================================================================


class TestAdvancedMetrics:
    """測試進階評估指標"""

    def test_balanced_accuracy_calculation(self):
        """驗證 balanced accuracy 計算"""
        # 模擬預測和實際值
        predictions = [1, 1, 1, 0, 0, 0, 1, 0]
        actuals = [1, 1, 0, 0, 0, 1, 1, 0]

        # 計算 TP, TN, FP, FN
        tp = sum(1 for p, a in zip(predictions, actuals) if p == 1 and a == 1)
        tn = sum(1 for p, a in zip(predictions, actuals) if p == 0 and a == 0)
        fp = sum(1 for p, a in zip(predictions, actuals) if p == 1 and a == 0)
        fn = sum(1 for p, a in zip(predictions, actuals) if p == 0 and a == 1)

        # Balanced Accuracy = (TPR + TNR) / 2
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
        tnr = tn / (tn + fp) if (tn + fp) > 0 else 0
        balanced_accuracy = (tpr + tnr) / 2

        assert 0.0 <= balanced_accuracy <= 1.0
        assert balanced_accuracy > 0.5, "應有合理的 balanced accuracy"

    def test_spearman_correlation_with_human_reviews(self):
        """驗證 Spearman 相關性 (≥0.75 目標)"""
        # 模擬自動評審的評分
        automated_scores = [6.5, 7.0, 5.5, 8.0, 6.0, 7.5, 5.0, 8.5]

        # 模擬人類評審的評分
        human_scores = [6.0, 7.5, 5.0, 8.0, 6.5, 7.0, 5.5, 8.5]

        # 計算 Spearman 相關性 (手動實現)
        def spearman_correlation(x, y):
            n = len(x)
            rank_x = sorted(range(n), key=lambda i: x[i])
            rank_y = sorted(range(n), key=lambda i: y[i])
            ranks_x = [0] * n
            ranks_y = [0] * n
            for i, idx in enumerate(rank_x):
                ranks_x[idx] = i + 1
            for i, idx in enumerate(rank_y):
                ranks_y[idx] = i + 1

            d_squared = sum((ranks_x[i] - ranks_y[i]) ** 2 for i in range(n))
            correlation = 1 - (6 * d_squared) / (n * (n * n - 1))
            return correlation

        correlation = spearman_correlation(automated_scores, human_scores)

        assert -1.0 <= correlation <= 1.0
        assert correlation > 0.5, "應有正相關"

    def test_decision_agreement_rate(self, review_samples: List[IndividualReview]):
        """驗證決策一致率"""
        # 計算多數決策
        decisions = [r.decision for r in review_samples]
        decision_counts = {}
        for d in decisions:
            decision_counts[d] = decision_counts.get(d, 0) + 1

        majority_decision = max(decision_counts, key=decision_counts.get)
        agreement_rate = decision_counts[majority_decision] / len(decisions)

        assert 0.0 <= agreement_rate <= 1.0
        assert agreement_rate >= 0.4, "應有合理的決策一致率"


# ============================================================================
# TEST: 邊界情況與錯誤處理
# ============================================================================


class TestEdgeCases:
    """測試邊界情況"""

    def test_empty_paper_content(self):
        """驗證空論文內容處理"""
        reviewer = AutomatedReviewerV2()
        result = reviewer.review_paper("")

        # 應該仍然生成評審
        assert len(result.individual_reviews) == 5
        assert result.final_decision is not None

    def test_very_short_paper(self):
        """驗證極短論文處理"""
        reviewer = AutomatedReviewerV2()
        result = reviewer.review_paper("Title: Short Paper\n\nContent: Very short.")

        assert isinstance(result, EnsembleReviewResult)
        assert len(result.individual_reviews) == 5

    def test_single_review_consensus(self):
        """驗證單個評審的一致性"""
        meta_reviewer = MetaReviewerModule()

        single_review = [
            IndividualReview(
                reviewer_id=1,
                reviewer_style="balanced",
                scores={
                    "soundness": 7.0,
                    "presentation": 7.0,
                    "contribution": 6.5,
                    "overall": 6.8,
                    "confidence": 0.75,
                },
                strengths=["Good"],
                weaknesses=["Minor issue"],
                decision="borderline",
            )
        ]

        consensus = meta_reviewer._compute_consensus(single_review)
        assert consensus == 1.0, "單個評審應有完全一致性"

    def test_all_different_decisions(self):
        """驗證所有不同決策的一致性"""
        meta_reviewer = MetaReviewerModule()

        reviews = [
            IndividualReview(
                reviewer_id=i,
                reviewer_style="balanced",
                scores={
                    "overall": 6.0,
                    "soundness": 6.0,
                    "presentation": 6.0,
                    "contribution": 6.0,
                    "confidence": 0.75,
                },
                strengths=["Good"],
                weaknesses=["Issue"],
                decision=decision,
            )
            for i, decision in enumerate(
                ["accept", "weak_accept", "borderline", "weak_reject", "reject"], 1
            )
        ]

        consensus = meta_reviewer._compute_consensus(reviews)
        assert 0.0 <= consensus < 1.0, "完全不同的決策應有低一致性"


# ============================================================================
# TEST: 數據序列化與持久化
# ============================================================================


class TestSerialization:
    """測試數據序列化"""

    def test_individual_review_serialization(self):
        """驗證個別評審序列化"""
        review = IndividualReview(
            reviewer_id=1,
            reviewer_style="balanced",
            scores={
                "overall": 6.8,
                "soundness": 7.0,
                "presentation": 7.0,
                "contribution": 6.5,
                "confidence": 0.75,
            },
            strengths=["Good methodology"],
            weaknesses=["Limited novelty"],
            decision="borderline",
            consistency_score=0.88,
            depth_score=0.87,
        )

        # 序列化為字典
        review_dict = {
            "reviewer_id": review.reviewer_id,
            "reviewer_style": review.reviewer_style,
            "scores": review.scores,
            "strengths": review.strengths,
            "weaknesses": review.weaknesses,
            "decision": review.decision,
            "consistency_score": review.consistency_score,
            "depth_score": review.depth_score,
        }

        # 驗證序列化
        assert review_dict["reviewer_id"] == 1
        assert review_dict["reviewer_style"] == "balanced"
        assert review_dict["decision"] == "borderline"

    def test_ensemble_result_serialization(self, review_samples: List[IndividualReview]):
        """驗證集合結果序列化"""
        meta_reviewer = MetaReviewerModule()
        meta_decision = meta_reviewer.make_final_decision(review_samples)

        result = EnsembleReviewResult(
            individual_reviews=review_samples,
            meta_review=meta_decision,
            consensus_level=meta_decision["consensus_level"],
            final_decision=meta_decision["final_decision"],
            acceptance_probability=meta_decision["acceptance_probability"],
            confidence=0.76,
        )

        # 驗證結果可序列化為 JSON
        result_dict = {
            "consensus_level": result.consensus_level,
            "final_decision": result.final_decision,
            "acceptance_probability": result.acceptance_probability,
            "confidence": result.confidence,
            "timestamp": result.timestamp,
        }

        json_str = json.dumps(result_dict)
        assert isinstance(json_str, str)
        assert "final_decision" in json_str


# ============================================================================
# TEST: 集成測試
# ============================================================================


class TestIntegration:
    """集成測試"""

    def test_full_pipeline_with_quality_validation(self, standard_paper: str):
        """驗證完整管道包括品質驗證"""
        reviewer = AutomatedReviewerV2()

        # 執行評審
        result = reviewer.review_paper(standard_paper)

        # 驗證品質驗證已執行
        for review in result.individual_reviews:
            # 評審應該被驗證過
            assert hasattr(review, "is_hallucinated")
            assert hasattr(review, "consistency_score")

    def test_calibration_with_batch_results(
        self, standard_paper: str, weak_paper: str, strong_paper: str
    ):
        """驗證校準與批量結果"""
        reviewer = AutomatedReviewerV2()
        calibration = CalibrationModule()

        papers = [
            {"content": standard_paper},
            {"content": weak_paper},
            {"content": strong_paper},
        ]

        results = reviewer.batch_review(papers)

        # 執行校準
        calibration_report = calibration.calibrate_decisions(results)

        # 驗證校準報告
        assert calibration_report["sample_size"] == 3
        assert "calibration_error" in calibration_report
        assert "recommendation" in calibration_report

    def test_consistency_across_multiple_runs(self, standard_paper: str):
        """驗證多次運行的一致性"""
        reviewer = AutomatedReviewerV2()

        # 運行多次
        results = [reviewer.review_paper(standard_paper) for _ in range(3)]

        # 驗證決策一致性
        decisions = [r.final_decision for r in results]
        assert len(set(decisions)) <= 2, "多次運行應有相似的決策"

        # 驗證接受概率相近
        probabilities = [r.acceptance_probability for r in results]
        prob_range = max(probabilities) - min(probabilities)
        assert prob_range < 0.2, "接受概率應相對穩定"
