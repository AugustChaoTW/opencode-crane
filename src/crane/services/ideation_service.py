"""
想法生成與多元性探索服務 (IdeationService)

基於 Nature 論文《The AI Scientist》的 ideation 階段設計。
從領域知識自動生成新穎且可執行的研究假設。

核心組件：
1. DomainKnowledgeGraphBuilder - 領域知識圖構建
2. IdeaGenerationEngine - 想法生成引擎
3. NoveltyDetectionModule - 新穎性檢測
4. ExecutabilityScorer - 可執行性評分
5. ImpactPredictor - 預期影響預測
6. MapElitesArchiveManager - Pareto 檔案管理
"""

import json
import logging
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ResearchIdea:
    """研究想法"""

    idea_id: str
    title: str
    description: str
    reasoning: str
    experimental_plan: str
    domain: str

    novelty_score: float
    executability_score: float
    impact_score: float

    similar_papers: List[str] = field(default_factory=list)
    estimated_compute_hours: float = 0.0
    required_datasets: List[str] = field(default_factory=list)
    estimated_implementation_days: float = 0.0

    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_stage: int = 0
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def pareto_dominates(self, other: "ResearchIdea") -> bool:
        """檢查是否 Pareto 支配另一個想法"""
        self_dims = [self.novelty_score, self.executability_score, self.impact_score]
        other_dims = [other.novelty_score, other.executability_score, other.impact_score]

        return all(s >= o for s, o in zip(self_dims, other_dims)) and any(
            s > o for s, o in zip(self_dims, other_dims)
        )


@dataclass
class IdeationArchive:
    """想法檔案 - Pareto 前沿維護"""

    ideas: List[ResearchIdea] = field(default_factory=list)
    pareto_frontier: List[str] = field(default_factory=list)
    best_novelty: Optional[ResearchIdea] = None
    best_executability: Optional[ResearchIdea] = None
    best_impact: Optional[ResearchIdea] = None
    total_ideas_generated: int = 0

    def add_idea(self, idea: ResearchIdea) -> bool:
        """添加想法到檔案，維護 Pareto 前沿"""
        self.ideas.append(idea)
        self.total_ideas_generated += 1

        if self.best_novelty is None or idea.novelty_score > self.best_novelty.novelty_score:
            self.best_novelty = idea

        if (
            self.best_executability is None
            or idea.executability_score > self.best_executability.executability_score
        ):
            self.best_executability = idea

        if self.best_impact is None or idea.impact_score > self.best_impact.impact_score:
            self.best_impact = idea

        self._update_pareto_frontier()
        return True

    def _update_pareto_frontier(self) -> None:
        """更新 Pareto 前沿"""
        frontier = []
        for idea in self.ideas:
            dominated = False
            for other in self.ideas:
                if other.idea_id != idea.idea_id and other.pareto_dominates(idea):
                    dominated = True
                    break
            if not dominated:
                frontier.append(idea.idea_id)
        self.pareto_frontier = frontier


class DomainKnowledgeGraphBuilder:
    """領域知識圖構建"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.concepts: Dict[str, Dict[str, Any]] = {}
        self.relations: Dict[Tuple[str, str], str] = {}

    def build_from_references(self, reference_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """從參考文獻庫構建知識圖"""
        for ref in reference_data:
            self._extract_concepts(ref)

        self.logger.info(f"構建知識圖：{len(self.concepts)} 個概念，{len(self.relations)} 個關係")

        return {
            "concepts": self.concepts,
            "relations": self.relations,
            "concept_count": len(self.concepts),
            "relation_count": len(self.relations),
        }

    def _extract_concepts(self, reference: Dict[str, Any]) -> None:
        """從論文中提取概念"""
        title = reference.get("title", "")
        keywords = reference.get("keywords", [])

        for keyword in keywords:
            if keyword not in self.concepts:
                self.concepts[keyword] = {
                    "frequency": 0,
                    "sources": [],
                    "type": "unknown",
                }
            self.concepts[keyword]["frequency"] += 1
            self.concepts[keyword]["sources"].append(reference.get("key", ""))

    def find_concept_gaps(self) -> List[Tuple[str, str]]:
        """識別未充分探索的概念交叉點"""
        gaps = []
        concepts = list(self.concepts.keys())

        for i, c1 in enumerate(concepts):
            for c2 in concepts[i + 1 :]:
                if (c1, c2) not in self.relations and (c2, c1) not in self.relations:
                    gaps.append((c1, c2))

        return gaps[:10]


class IdeaGenerationEngine:
    """想法生成引擎"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.generated_ideas: List[ResearchIdea] = []

    def generate_ideas(
        self, domain: str, knowledge_graph: Dict[str, Any], num_ideas: int = 20
    ) -> List[ResearchIdea]:
        """生成想法"""
        ideas = []

        concepts = list(knowledge_graph.get("concepts", {}).keys())
        gaps = knowledge_graph.get("gaps", [])

        for i in range(num_ideas):
            idea = self._create_idea(domain, concepts, gaps, i)
            ideas.append(idea)
            self.generated_ideas.append(idea)

        self.logger.info(f"生成 {len(ideas)} 個想法")
        return ideas

    def _create_idea(
        self, domain: str, concepts: List[str], gaps: List[Tuple[str, str]], idx: int
    ) -> ResearchIdea:
        """創建單個想法"""
        import random

        concept1 = random.choice(concepts) if concepts else "Method"
        concept2 = random.choice(concepts) if concepts else "Dataset"

        idea_id = f"idea_{domain}_{idx}_{datetime.now().timestamp()}"
        title = f"Novel {concept1} Approach for {concept2} in {domain}"

        return ResearchIdea(
            idea_id=idea_id,
            title=title,
            description=f"Combining {concept1} with {concept2} to advance {domain} research",
            reasoning=f"Recent progress in {concept1} suggests potential synergy with {concept2}",
            experimental_plan="Compare against baselines on standard benchmarks with ablation studies",
            domain=domain,
            novelty_score=0.65,
            executability_score=0.70,
            impact_score=0.60,
            estimated_compute_hours=48,
            required_datasets=["CIFAR10", "ImageNet"],
            estimated_implementation_days=5,
            generation_stage=1,
        )


class NoveltyDetectionModule:
    """新穎性檢測"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.known_papers: Set[str] = set()

    def load_paper_embeddings(self, references: List[Dict[str, Any]]) -> None:
        """加載論文向量"""
        for ref in references:
            self.known_papers.add(ref.get("key", ""))
        self.logger.info(f"加載 {len(self.known_papers)} 篇論文用於新穎性檢測")

    def compute_novelty_score(self, idea: ResearchIdea, similar_papers: List[str]) -> float:
        """計算新穎性分數"""
        if not similar_papers:
            return 1.0

        max_similarity = len(similar_papers) / max(len(self.known_papers), 1)
        novelty = 1.0 - min(max_similarity, 0.9)

        idea.similar_papers = similar_papers[:5]
        return novelty

    def detect_duplicates(self, idea: ResearchIdea, threshold: float = 0.85) -> bool:
        """檢測重複想法"""
        if len(idea.similar_papers) > 0:
            similarity = len(idea.similar_papers) / max(len(self.known_papers), 1)
            return similarity > threshold
        return False


class ExecutabilityScorer:
    """可執行性評分"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def score_executability(
        self, idea: ResearchIdea, resource_constraints: Dict[str, float]
    ) -> float:
        """評分可執行性"""
        max_compute_hours = resource_constraints.get("max_compute_hours", 100)
        max_implementation_days = resource_constraints.get("max_implementation_days", 30)

        compute_score = 1.0 - min(idea.estimated_compute_hours / max_compute_hours, 1.0)
        impl_score = 1.0 - min(idea.estimated_implementation_days / max_implementation_days, 1.0)

        dataset_score = (
            1.0
            if all(
                d in ["CIFAR10", "ImageNet", "Wikipedia", "MNIST"] for d in idea.required_datasets
            )
            else 0.7
        )

        executability = (compute_score + impl_score + dataset_score) / 3.0
        return max(0.0, min(1.0, executability))


class ImpactPredictor:
    """預期影響預測"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def predict_impact(self, idea: ResearchIdea, domain_trends: Dict[str, Any]) -> float:
        """預測想法的影響"""
        keyword_impact = domain_trends.get("trending_keywords", {})

        impact_score = 0.5
        for keyword in idea.title.split():
            if keyword in keyword_impact:
                impact_score += keyword_impact[keyword] * 0.1

        idea_type_impact = {"novel": 0.2, "efficient": 0.15, "robust": 0.12}
        for term, boost in idea_type_impact.items():
            if term in idea.description.lower():
                impact_score += boost

        return max(0.0, min(1.0, impact_score))


class MapElitesArchiveManager:
    """Map-Elites 檔案管理"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.archive = IdeationArchive()

    def add_idea_to_archive(self, idea: ResearchIdea) -> bool:
        """添加想法並維護 Pareto 前沿"""
        self.archive.add_idea(idea)

        removed_count = self._prune_dominated_ideas()
        if removed_count > 0:
            self.logger.info(f"移除了 {removed_count} 個被支配的想法")

        return True

    def _prune_dominated_ideas(self) -> int:
        """移除被支配的想法"""
        initial_count = len(self.archive.ideas)

        self.archive.ideas = [
            idea for idea in self.archive.ideas if idea.idea_id in self.archive.pareto_frontier
        ]

        return initial_count - len(self.archive.ideas)

    def get_frontier_ideas(self) -> List[ResearchIdea]:
        """獲取 Pareto 前沿上的想法"""
        return [idea for idea in self.archive.ideas if idea.idea_id in self.archive.pareto_frontier]

    def get_archive_snapshot(self) -> Dict[str, Any]:
        """獲取檔案快照"""
        return {
            "total_ideas": len(self.archive.ideas),
            "frontier_size": len(self.archive.pareto_frontier),
            "best_novelty": asdict(self.archive.best_novelty)
            if self.archive.best_novelty
            else None,
            "best_executability": asdict(self.archive.best_executability)
            if self.archive.best_executability
            else None,
            "best_impact": asdict(self.archive.best_impact) if self.archive.best_impact else None,
        }


class IdeationService:
    """想法生成與多元性探索服務"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.kg_builder = DomainKnowledgeGraphBuilder()
        self.idea_engine = IdeaGenerationEngine()
        self.novelty_detector = NoveltyDetectionModule()
        self.executability_scorer = ExecutabilityScorer()
        self.impact_predictor = ImpactPredictor()
        self.archive_manager = MapElitesArchiveManager()

    def run_ideation_pipeline(
        self,
        domain: str,
        references: List[Dict[str, Any]],
        resource_constraints: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """執行完整的想法生成管道"""
        if resource_constraints is None:
            resource_constraints = {"max_compute_hours": 100, "max_implementation_days": 30}

        self.logger.info(f"開始 {domain} 領域的想法生成")

        self.novelty_detector.load_paper_embeddings(references)

        kg = self.kg_builder.build_from_references(references)
        kg["gaps"] = self.kg_builder.find_concept_gaps()

        ideas = self.idea_engine.generate_ideas(domain, kg, num_ideas=20)

        for idea in ideas:
            novelty_score = self.novelty_detector.compute_novelty_score(idea, [])
            idea.novelty_score = max(0.0, novelty_score)

            executability = self.executability_scorer.score_executability(
                idea, resource_constraints
            )
            idea.executability_score = executability

            domain_trends = {"trending_keywords": {}}
            impact = self.impact_predictor.predict_impact(idea, domain_trends)
            idea.impact_score = impact

            is_duplicate = self.novelty_detector.detect_duplicates(idea)
            if not is_duplicate:
                self.archive_manager.add_idea_to_archive(idea)

        return self._generate_ideation_report()

    def _generate_ideation_report(self) -> Dict[str, Any]:
        """生成想法生成報告"""
        frontier_ideas = self.archive_manager.get_frontier_ideas()

        return {
            "success": True,
            "total_ideas_generated": len(self.idea_engine.generated_ideas),
            "ideas_in_frontier": len(frontier_ideas),
            "archive_snapshot": self.archive_manager.get_archive_snapshot(),
            "frontier_ideas": [idea.to_dict() for idea in frontier_ideas],
            "timestamp": datetime.now().isoformat(),
        }

    def get_top_ideas(self, metric: str = "impact", top_k: int = 5) -> List[ResearchIdea]:
        """獲取排名靠前的想法"""
        frontier_ideas = self.archive_manager.get_frontier_ideas()

        if metric == "novelty":
            sorted_ideas = sorted(frontier_ideas, key=lambda x: x.novelty_score, reverse=True)
        elif metric == "executability":
            sorted_ideas = sorted(frontier_ideas, key=lambda x: x.executability_score, reverse=True)
        else:
            sorted_ideas = sorted(frontier_ideas, key=lambda x: x.impact_score, reverse=True)

        return sorted_ideas[:top_k]
