from __future__ import annotations

from contextlib import contextmanager
import importlib
import math
from pathlib import Path
import re

import yaml


def _load_models():
    return importlib.import_module("crane.models.paper_profile")


def _load_service():
    return importlib.import_module("crane.services.journal_matching_service")


_models = _load_models()
PaperProfile = _models.PaperProfile
PaperType = _models.PaperType
EvidencePattern = _models.EvidencePattern
NoveltyShape = _models.NoveltyShape
JournalMatchingService = _load_service().JournalMatchingService


@contextmanager
def _raises(error_type: type[BaseException], match: str = ""):
    try:
        yield
    except error_type as error:
        if match and re.search(match, str(error)) is None:
            raise AssertionError(f"Expected message to match {match!r}, got {error!r}") from error
        return
    except Exception as error:
        raise AssertionError(
            f"Expected {error_type.__name__}, got {type(error).__name__}"
        ) from error
    raise AssertionError(f"Expected {error_type.__name__} to be raised")


def _assert_close(actual: float, expected: float, tol: float = 1e-9) -> None:
    assert math.isclose(actual, expected, rel_tol=tol, abs_tol=tol)


def _write_profiles(tmp_path: Path, journals: list[dict]) -> Path:
    path = tmp_path / "profiles.yaml"
    path.write_text(yaml.safe_dump({"journals": journals}, sort_keys=False), encoding="utf-8")
    return path


def _base_journal(name: str = "J1") -> dict:
    return {
        "name": name,
        "abbreviation": name,
        "publisher": "P",
        "quartile": "Q1",
        "impact_factor": 10.0,
        "scope_keywords": ["machine learning", "optimization"],
        "preferred_paper_types": ["empirical", "system"],
        "preferred_method_families": ["deep learning"],
        "preferred_evidence_patterns": ["benchmark_heavy"],
        "typical_word_count": [6000, 10000],
        "review_timeline_months": [3, 6],
        "acceptance_rate": 0.2,
        "apc_usd": 0,
        "open_access": False,
        "open_access_type": "subscription",
        "waiver_available": False,
        "desk_reject_signals": ["no experiments", "incremental contribution", "poor baselines"],
        "citation_venues": ["NeurIPS", "ICML", "ICLR"],
    }


def _profile(**overrides: object) -> PaperProfile:
    base = {
        "paper_type": PaperType.EMPIRICAL,
        "method_family": "deep learning",
        "evidence_pattern": EvidencePattern.BENCHMARK_HEAVY,
        "validation_scale": "large",
        "citation_neighborhood": ["NeurIPS", "ICML"],
        "novelty_shape": NoveltyShape.NEW_METHOD,
        "problem_domain": "machine learning",
        "keywords": ["machine learning", "optimization"],
        "word_count": 8000,
        "num_references": 40,
    }
    base.update(overrides)
    return PaperProfile(**base)


class TestYamlLoadingValidation:
    def test_raises_when_file_missing(self, tmp_path: Path):
        missing = tmp_path / "missing.yaml"
        with _raises(FileNotFoundError):
            JournalMatchingService(missing)

    def test_raises_when_root_is_not_mapping(self, tmp_path: Path):
        path = tmp_path / "bad.yaml"
        path.write_text("- journals\n", encoding="utf-8")
        with _raises(ValueError, match="mapping"):
            JournalMatchingService(path)

    def test_raises_when_journals_not_list(self, tmp_path: Path):
        path = tmp_path / "bad.yaml"
        path.write_text("journals: {}\n", encoding="utf-8")
        with _raises(ValueError, match="must be a list"):
            JournalMatchingService(path)

    def test_raises_when_entry_not_mapping(self, tmp_path: Path):
        path = tmp_path / "bad.yaml"
        path.write_text("journals:\n  - 1\n", encoding="utf-8")
        with _raises(ValueError, match="must be a mapping"):
            JournalMatchingService(path)

    def test_raises_when_required_field_missing(self, tmp_path: Path):
        journal = _base_journal()
        journal.pop("scope_keywords")
        path = _write_profiles(tmp_path, [journal])
        with _raises(ValueError, match="missing required fields"):
            JournalMatchingService(path)

    def test_raises_when_scope_keywords_not_list(self, tmp_path: Path):
        journal = _base_journal()
        journal["scope_keywords"] = "x"
        path = _write_profiles(tmp_path, [journal])
        with _raises(ValueError, match="scope_keywords"):
            JournalMatchingService(path)

    def test_raises_when_preferred_paper_types_not_list(self, tmp_path: Path):
        journal = _base_journal()
        journal["preferred_paper_types"] = "empirical"
        path = _write_profiles(tmp_path, [journal])
        with _raises(ValueError, match="preferred_paper_types"):
            JournalMatchingService(path)

    def test_raises_when_evidence_patterns_not_list(self, tmp_path: Path):
        journal = _base_journal()
        journal["preferred_evidence_patterns"] = "benchmark_heavy"
        path = _write_profiles(tmp_path, [journal])
        with _raises(ValueError, match="preferred_evidence_patterns"):
            JournalMatchingService(path)

    def test_raises_when_citation_venues_not_list(self, tmp_path: Path):
        journal = _base_journal()
        journal["citation_venues"] = "NeurIPS"
        path = _write_profiles(tmp_path, [journal])
        with _raises(ValueError, match="citation_venues"):
            JournalMatchingService(path)

    def test_raises_when_typical_word_count_invalid(self, tmp_path: Path):
        journal = _base_journal()
        journal["typical_word_count"] = [1000]
        path = _write_profiles(tmp_path, [journal])
        with _raises(ValueError, match="typical_word_count"):
            JournalMatchingService(path)

    def test_loads_valid_profiles(self, tmp_path: Path):
        path = _write_profiles(tmp_path, [_base_journal("A"), _base_journal("B")])
        svc = JournalMatchingService(path)
        assert len(svc.journals) == 2

    def test_loads_project_profiles_file(self):
        path = Path("data/journals/q1_journal_profiles.yaml")
        svc = JournalMatchingService(path)
        assert len(svc.journals) == 55


class TestScopeFit:
    def test_scope_fit_full_overlap(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        score = svc.calculate_scope_fit(_profile(), svc.journals[0])
        assert score == 1.0

    def test_scope_fit_partial_overlap(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(keywords=["machine learning", "statistics"], problem_domain="nlp")
        score = svc.calculate_scope_fit(p, svc.journals[0])
        _assert_close(score, 1 / 4)

    def test_scope_fit_no_overlap(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(keywords=["software"], problem_domain="distributed systems")
        assert svc.calculate_scope_fit(p, svc.journals[0]) == 0.0

    def test_scope_fit_empty_paper_terms(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(keywords=[], problem_domain="")
        assert svc.calculate_scope_fit(p, svc.journals[0]) == 0.0

    def test_scope_fit_empty_journal_terms(self, tmp_path: Path):
        j = _base_journal()
        j["scope_keywords"] = []
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        assert svc.calculate_scope_fit(_profile(), svc.journals[0]) == 0.0


class TestContributionStyleFit:
    def test_exact_match(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        assert svc.calculate_contribution_style_fit(_profile(), svc.journals[0]) == 1.0

    def test_unknown_type(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(paper_type=PaperType.UNKNOWN)
        assert svc.calculate_contribution_style_fit(p, svc.journals[0]) == 0.0

    def test_partial_match_theoretical(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(paper_type=PaperType.THEORETICAL)
        assert svc.calculate_contribution_style_fit(p, svc.journals[0]) == 0.5

    def test_partial_match_system_with_application_preference(self, tmp_path: Path):
        j = _base_journal()
        j["preferred_paper_types"] = ["application"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        p = _profile(paper_type=PaperType.SYSTEM)
        assert svc.calculate_contribution_style_fit(p, svc.journals[0]) == 0.5

    def test_mismatch(self, tmp_path: Path):
        j = _base_journal()
        j["preferred_paper_types"] = ["survey"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        p = _profile(paper_type=PaperType.SYSTEM)
        assert svc.calculate_contribution_style_fit(p, svc.journals[0]) == 0.0


class TestEvaluationStyleFit:
    def test_exact_match(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        assert svc.calculate_evaluation_style_fit(_profile(), svc.journals[0]) == 1.0

    def test_mixed_profile_returns_half(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(evidence_pattern=EvidencePattern.MIXED)
        assert svc.calculate_evaluation_style_fit(p, svc.journals[0]) == 0.5

    def test_journal_prefers_mixed_returns_half(self, tmp_path: Path):
        j = _base_journal()
        j["preferred_evidence_patterns"] = ["mixed"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        assert svc.calculate_evaluation_style_fit(_profile(), svc.journals[0]) == 0.5

    def test_unknown_returns_zero(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(evidence_pattern=EvidencePattern.UNKNOWN)
        assert svc.calculate_evaluation_style_fit(p, svc.journals[0]) == 0.0

    def test_mismatch_returns_zero(self, tmp_path: Path):
        j = _base_journal()
        j["preferred_evidence_patterns"] = ["theorem_heavy"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        assert svc.calculate_evaluation_style_fit(_profile(), svc.journals[0]) == 0.0


class TestCitationNeighborhoodFit:
    def test_full_overlap(self, tmp_path: Path):
        j = _base_journal()
        j["citation_venues"] = ["NeurIPS", "ICML"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        assert svc.calculate_citation_neighborhood_fit(_profile(), svc.journals[0]) == 1.0

    def test_partial_overlap(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        score = svc.calculate_citation_neighborhood_fit(_profile(), svc.journals[0])
        _assert_close(score, 2 / 3)

    def test_no_paper_venues(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(citation_neighborhood=[])
        assert svc.calculate_citation_neighborhood_fit(p, svc.journals[0]) == 0.0

    def test_no_journal_venues(self, tmp_path: Path):
        j = _base_journal()
        j["citation_venues"] = []
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        assert svc.calculate_citation_neighborhood_fit(_profile(), svc.journals[0]) == 0.0

    def test_case_and_whitespace_normalization(self, tmp_path: Path):
        j = _base_journal()
        j["citation_venues"] = [" neurips ", "icml"]
        p = _profile(citation_neighborhood=["NEURIPS", " ICML "])
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        assert svc.calculate_citation_neighborhood_fit(p, svc.journals[0]) == 1.0


class TestOperationalFit:
    def test_word_count_in_range(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        assert svc.calculate_operational_fit(_profile(word_count=7000), svc.journals[0]) == 1.0

    def test_word_count_below_range_linear_decay(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        score = svc.calculate_operational_fit(_profile(word_count=3000), svc.journals[0])
        _assert_close(score, 0.5)

    def test_word_count_above_range_linear_decay(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        score = svc.calculate_operational_fit(_profile(word_count=12000), svc.journals[0])
        _assert_close(score, 0.8)

    def test_word_count_far_above_clamps_to_zero(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        assert svc.calculate_operational_fit(_profile(word_count=25000), svc.journals[0]) == 0.0

    def test_invalid_word_range_returns_zero(self, tmp_path: Path):
        j = _base_journal()
        j["typical_word_count"] = [10000, 6000]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        assert svc.calculate_operational_fit(_profile(), svc.journals[0]) == 0.0

    def test_negative_word_count_is_clamped(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        assert svc.calculate_operational_fit(_profile(word_count=-5), svc.journals[0]) == 0.0


class TestDeskRejectRisk:
    def test_no_signals_has_zero_risk(self, tmp_path: Path):
        j = _base_journal()
        j["desk_reject_signals"] = []
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        risk, factors = svc.assess_desk_reject_risk(_profile(), svc.journals[0])
        assert risk == 0.0
        assert factors == []

    def test_no_experiments_signal_triggered(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(evidence_pattern=EvidencePattern.THEOREM_HEAVY)
        risk, factors = svc.assess_desk_reject_risk(p, svc.journals[0])
        assert "no experiments" in factors
        assert risk > 0.0

    def test_incremental_signal_triggered(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(novelty_shape=NoveltyShape.INCREMENTAL)
        _, factors = svc.assess_desk_reject_risk(p, svc.journals[0])
        assert "incremental contribution" in factors

    def test_poor_baselines_signal_triggered(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(evidence_pattern=EvidencePattern.THEOREM_HEAVY)
        _, factors = svc.assess_desk_reject_risk(p, svc.journals[0])
        assert "poor baselines" in factors

    def test_insufficient_validation_signal_triggered(self, tmp_path: Path):
        j = _base_journal()
        j["desk_reject_signals"] = ["insufficient validation"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        p = _profile(num_references=10)
        _, factors = svc.assess_desk_reject_risk(p, svc.journals[0])
        assert "insufficient validation" in factors

    def test_scalability_signal_triggered(self, tmp_path: Path):
        j = _base_journal()
        j["desk_reject_signals"] = ["insufficient scalability"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        p = _profile(validation_scale="small")
        _, factors = svc.assess_desk_reject_risk(p, svc.journals[0])
        assert "insufficient scalability" in factors

    def test_relevance_signal_triggered(self, tmp_path: Path):
        j = _base_journal()
        j["desk_reject_signals"] = ["limited software engineering relevance"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        p = _profile(problem_domain="")
        _, factors = svc.assess_desk_reject_risk(p, svc.journals[0])
        assert "limited software engineering relevance" in factors

    def test_deduplicates_factors(self, tmp_path: Path):
        j = _base_journal()
        j["desk_reject_signals"] = ["incremental contribution", "incremental contribution"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j]))
        p = _profile(novelty_shape=NoveltyShape.INCREMENTAL)
        risk, factors = svc.assess_desk_reject_risk(p, svc.journals[0])
        assert factors == ["incremental contribution"]
        _assert_close(risk, 0.5)


class TestMatchAndTop3:
    def test_match_returns_sorted_and_labels(self, tmp_path: Path):
        j1 = _base_journal("J1")
        j2 = _base_journal("J2")
        j2["scope_keywords"] = ["software engineering"]
        j3 = _base_journal("J3")
        j3["scope_keywords"] = ["biology"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [j3, j2, j1]))

        fits = svc.match(_profile())

        assert len(fits) == 3
        assert fits[0].overall_fit >= fits[1].overall_fit >= fits[2].overall_fit
        assert fits[0].recommendation == "target"
        assert fits[1].recommendation == "backup"
        assert fits[2].recommendation == "safe"

    def test_match_uses_weighted_overall_formula(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        fit = svc.match(_profile())[0]
        expected = (
            0.35 * fit.scope_fit
            + 0.20 * fit.contribution_style_fit
            + 0.20 * fit.evaluation_style_fit
            + 0.15 * fit.citation_neighborhood_fit
            + 0.10 * fit.operational_fit
        )
        _assert_close(fit.overall_fit, expected)

    def test_recommend_top3_with_less_than_three(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal("Only")]))
        top3 = svc.recommend_top3(_profile())
        assert top3["target"] is not None
        assert top3["backup"] is None
        assert top3["safe"] is None

    def test_recommend_top3_full(self, tmp_path: Path):
        svc = JournalMatchingService(
            _write_profiles(tmp_path, [_base_journal("A"), _base_journal("B"), _base_journal("C")])
        )
        top3 = svc.recommend_top3(_profile())
        assert top3["target"] is not None
        assert top3["backup"] is not None
        assert top3["safe"] is not None

    def test_empty_profile_still_returns_fits(self, tmp_path: Path):
        svc = JournalMatchingService(
            _write_profiles(tmp_path, [_base_journal("A"), _base_journal("B")])
        )
        p = PaperProfile()
        fits = svc.match(p)
        assert len(fits) == 2
        assert all(0.0 <= f.overall_fit <= 1.0 for f in fits)

    def test_unknown_type_no_keywords_no_citations(self, tmp_path: Path):
        svc = JournalMatchingService(_write_profiles(tmp_path, [_base_journal()]))
        p = _profile(
            paper_type=PaperType.UNKNOWN,
            keywords=[],
            problem_domain="",
            citation_neighborhood=[],
        )
        fit = svc.match(p)[0]
        assert fit.scope_fit == 0.0
        assert fit.contribution_style_fit == 0.0
        assert fit.citation_neighborhood_fit == 0.0

    def test_tie_breaks_by_lower_risk(self, tmp_path: Path):
        a = _base_journal("A")
        b = _base_journal("B")
        a["desk_reject_signals"] = ["incremental contribution"]
        b["desk_reject_signals"] = ["weak novelty"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [a, b]))
        p = _profile(novelty_shape=NoveltyShape.NEW_METHOD)
        fits = svc.match(p)
        assert fits[0].desk_reject_risk <= fits[1].desk_reject_risk

    def test_known_profile_prefers_vision_journal(self):
        svc = JournalMatchingService(Path("data/journals/q1_journal_profiles.yaml"))
        p = _profile(
            paper_type=PaperType.EMPIRICAL,
            keywords=["computer vision", "pattern recognition", "image processing"],
            problem_domain="computer vision",
            citation_neighborhood=["CVPR", "ICCV", "ECCV"],
            evidence_pattern=EvidencePattern.BENCHMARK_HEAVY,
        )
        top = svc.match(p)[0]
        assert top.journal_name in {
            "IEEE Transactions on Pattern Analysis and Machine Intelligence",
            "International Journal of Computer Vision",
            "Pattern Recognition",
        }

    def test_match_with_budget_prioritizes_affordable_journals(self, tmp_path: Path):
        expensive = _base_journal("Expensive")
        expensive["apc_usd"] = 3500
        expensive["open_access_type"] = "hybrid"
        free = _base_journal("Free")
        free["apc_usd"] = 0
        free["open_access_type"] = "subscription"
        svc = JournalMatchingService(_write_profiles(tmp_path, [expensive, free]))

        fits = svc.match(_profile(), budget_usd=1000)

        assert fits[0].journal_name == "Free"
        assert fits[0].cost_assessment is not None
        assert fits[0].cost_assessment.affordability_status == "within_budget"
        assert fits[1].cost_assessment is not None
        assert fits[1].cost_assessment.affordability_status in {"over_budget", "waiver_possible"}

    def test_match_without_budget_keeps_legacy_ordering(self, tmp_path: Path):
        a = _base_journal("A")
        b = _base_journal("B")
        b["scope_keywords"] = ["other"]
        svc = JournalMatchingService(_write_profiles(tmp_path, [b, a]))

        legacy = svc.match(_profile())
        budgeted = svc.match(_profile(), budget_usd=1000)

        assert legacy[0].journal_name == "A"
        assert budgeted[0].journal_name == "A"
        assert legacy[0].overall_fit >= legacy[1].overall_fit

    def test_recommend_top3_with_budget(self, tmp_path: Path):
        j1 = _base_journal("J1")
        j1["apc_usd"] = 5000
        j1["open_access_type"] = "hybrid"
        j2 = _base_journal("J2")
        j2["apc_usd"] = 900
        j2["open_access_type"] = "hybrid"
        j3 = _base_journal("J3")
        j3["apc_usd"] = 0
        j3["open_access_type"] = "subscription"
        svc = JournalMatchingService(_write_profiles(tmp_path, [j1, j2, j3]))

        rec = svc.recommend_top3(_profile(), budget_usd=1000)

        assert rec["target"] is not None
        assert rec["target"].journal_name in {"J2", "J3"}
        assert rec["safe"] is not None

    def test_budget_zero_marks_non_free_as_over_budget(self, tmp_path: Path):
        free = _base_journal("Free")
        free["apc_usd"] = 0
        free["open_access_type"] = "subscription"
        paid = _base_journal("Paid")
        paid["apc_usd"] = 100
        paid["open_access_type"] = "hybrid"
        svc = JournalMatchingService(_write_profiles(tmp_path, [paid, free]))

        fits = svc.match(_profile(), budget_usd=0)

        assert fits[0].journal_name == "Free"
        assert fits[0].cost_assessment is not None
        assert fits[0].cost_assessment.affordability_status == "within_budget"
        assert fits[1].cost_assessment is not None
        assert fits[1].cost_assessment.affordability_status in {"over_budget", "waiver_possible"}
