# pyright: reportMissingImports=false
from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from crane.services.journal_recommender import JournalRecommender
from crane.services.reference_service import ReferenceService


@pytest.fixture
def refs_dir(tmp_path: Path) -> Path:
    refs = tmp_path / "references"
    (refs / "papers").mkdir(parents=True)
    (refs / "pdfs").mkdir(parents=True)
    (refs / "bibliography.bib").write_text("", encoding="utf-8")
    return refs


@pytest.fixture
def ref_service(refs_dir: Path) -> ReferenceService:
    return ReferenceService(refs_dir)


@pytest.fixture
def recommender() -> JournalRecommender:
    return JournalRecommender()


class TestAnalyzeCitedJournals:
    def test_counts_and_normalizes_aliases(
        self,
        recommender: JournalRecommender,
        ref_service: ReferenceService,
    ):
        ref_service.add(
            key="vaswani2017-attention",
            title="Attention Is All You Need",
            authors=["Vaswani"],
            year=2017,
            venue="NeurIPS",
        )
        ref_service.add(
            key="brown2020-language",
            title="Language Models are Few-Shot Learners",
            authors=["Brown"],
            year=2020,
            venue="Neural Information Processing Systems",
        )
        ref_service.add(
            key="li2023-vision",
            title="A Vision Paper",
            authors=["Li"],
            year=2023,
            venue="CVPR",
        )

        result = recommender.analyze_cited_journals(ref_service.refs_path)

        assert result["Neural Information Processing Systems"] == 2
        assert result["IEEE/CVF Conference on Computer Vision and Pattern Recognition"] == 1


class TestQueryJournalMetrics:
    def test_parses_best_match_from_openalex(
        self,
        recommender: JournalRecommender,
        monkeypatch: pytest.MonkeyPatch,
    ):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "results": [
                        {
                            "id": "https://openalex.org/S1",
                            "display_name": "Pattern Recognition Letters",
                            "works_count": 100,
                            "cited_by_count": 500,
                            "summary_stats": {"h_index": 10, "2yr_mean_citedness": 1.2},
                        },
                        {
                            "id": "https://openalex.org/S2",
                            "display_name": "Neural Information Processing Systems",
                            "abbreviated_title": "NeurIPS",
                            "works_count": 2500,
                            "cited_by_count": 90000,
                            "summary_stats": {"h_index": 250, "2yr_mean_citedness": 12.4},
                            "is_in_doaj": False,
                        },
                    ]
                }

        def fake_get(*args, **kwargs):
            return Response()

        monkeypatch.setattr("crane.services.journal_recommender.requests.get", fake_get)

        result = recommender.query_journal_metrics("NeurIPS")

        assert result["full_name"] == "Neural Information Processing Systems"
        assert result["works_count"] == 2500
        assert result["h_index"] == 250


class TestCalculateRelevanceScore:
    def test_prefers_cited_topical_venue(self, recommender: JournalRecommender):
        ml_journal = {
            "full_name": "Neural Information Processing Systems",
            "abbr": "NIPS",
            "quartile": "Q1",
            "acceptance_rate": 0.26,
            "topics": ["machine learning", "deep learning", "optimization"],
            "aliases": ["NeurIPS", "NIPS"],
            "openalex_metrics": {"cited_by_count": 90000, "h_index": 250},
        }
        vision_journal = {
            "full_name": "IEEE/CVF Conference on Computer Vision and Pattern Recognition",
            "abbr": "CVPR",
            "quartile": "Q1",
            "acceptance_rate": 0.24,
            "topics": ["computer vision", "image recognition"],
            "aliases": ["CVPR"],
            "openalex_metrics": {"cited_by_count": 95000, "h_index": 260},
        }
        cited = {
            "Neural Information Processing Systems": 3,
            "Journal of Machine Learning Research": 1,
        }

        ml_score = recommender.calculate_relevance_score(
            ml_journal,
            "deep learning transformers optimization language modeling",
            cited,
        )
        vision_score = recommender.calculate_relevance_score(
            vision_journal,
            "deep learning transformers optimization language modeling",
            cited,
        )

        assert 0.0 <= ml_score <= 1.0
        assert ml_score > vision_score


class TestRecommend:
    def test_returns_top_five_structured_recommendations(
        self,
        recommender: JournalRecommender,
        ref_service: ReferenceService,
        monkeypatch: pytest.MonkeyPatch,
    ):
        for key, venue in [
            ("paper1", "NeurIPS"),
            ("paper2", "ICML"),
            ("paper3", "Journal of Machine Learning Research"),
            ("paper4", "AAAI"),
        ]:
            ref_service.add(
                key=key,
                title=f"Sample {key}",
                authors=["Author"],
                year=2024,
                venue=venue,
            )

        fake_metrics = {
            "Neural Information Processing Systems": {"cited_by_count": 90000, "h_index": 250},
            "International Conference on Machine Learning": {
                "cited_by_count": 85000,
                "h_index": 230,
            },
            "Journal of Machine Learning Research": {"cited_by_count": 40000, "h_index": 220},
            "AAAI Conference on Artificial Intelligence": {
                "cited_by_count": 50000,
                "h_index": 210,
            },
        }

        monkeypatch.setattr(
            recommender,
            "query_journal_metrics",
            lambda name: fake_metrics.get(name, {"cited_by_count": 10000, "h_index": 100}),
        )

        result = recommender.recommend(
            "We present a transformer-based deep learning system for language modeling, "
            "representation learning, and optimization in machine learning tasks.",
            ref_service.refs_path,
        )

        assert len(result) == 5
        assert result[0]["full_name"] == "Neural Information Processing Systems"
        assert set(result[0]) == {
            "abbr",
            "full_name",
            "acceptance_rate",
            "relevance_score",
            "quartile",
        }
        assert result[0]["abbr"] == "NIPS"
        assert len(result[0]["abbr"]) <= 5
        assert all(0.0 <= item["relevance_score"] <= 1.0 for item in result)


class TestFindSimilarPapersInJournal:
    def test_returns_not_found_payload_when_metrics_missing(
        self, recommender: JournalRecommender, monkeypatch
    ):
        monkeypatch.setattr(recommender, "query_journal_metrics", lambda *_: {})

        result = recommender.find_similar_papers_in_journal(["repair"], "Unknown Journal")

        assert result["match_count"] == 0
        assert result["recommendation"] == "Journal not found in database"

    def test_returns_api_failure_payload(self, recommender: JournalRecommender, monkeypatch):
        monkeypatch.setattr(
            recommender,
            "query_journal_metrics",
            lambda *_: {"id": "https://openalex.org/S1", "full_name": "TMLR"},
        )
        monkeypatch.setattr(
            "crane.services.journal_recommender.requests.get",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("api down")),
        )

        result = recommender.find_similar_papers_in_journal(["repair"], "TMLR")

        assert result["journal"] == "TMLR"
        assert result["recommendation"] == "Failed to query OpenAlex API"

    def test_returns_sorted_matches_with_keywords(
        self, recommender: JournalRecommender, monkeypatch
    ):
        monkeypatch.setattr(
            recommender,
            "query_journal_metrics",
            lambda *_: {"id": "https://openalex.org/S1", "full_name": "TMLR"},
        )

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "results": [
                        {
                            "title": "Repair validation for language models",
                            "publication_year": 2025,
                            "doi": "https://doi.org/10.1000/a",
                            "id": "https://openalex.org/W1",
                            "abstract_inverted_index": {"repair": [0], "validation": [1]},
                            "authorships": [{"author": {"display_name": "Alice"}}],
                        },
                        {
                            "title": "Repair only",
                            "publication_year": 2024,
                            "doi": "",
                            "id": "https://openalex.org/W2",
                            "abstract_inverted_index": {"repair": [0]},
                            "authorships": [{"author": {"display_name": "Bob"}}],
                        },
                    ]
                }

        monkeypatch.setattr(
            "crane.services.journal_recommender.requests.get", lambda *args, **kwargs: Response()
        )

        result = recommender.find_similar_papers_in_journal(["repair", "validation"], "TMLR")

        assert result["match_count"] == 2
        assert result["keywords_matched"] == ["repair", "validation"]
        assert result["similar_papers"][0]["title"] == "Repair validation for language models"
        assert result["similar_papers"][1]["url"] == "https://openalex.org/W2"
        assert result["recommendation"].startswith("MODERATE FIT")


class TestJournalRecommenderHelpers:
    def test_load_candidates_raises_when_snapshot_missing(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="SJR snapshot not found"):
            JournalRecommender(tmp_path)

    def test_load_candidates_merges_template_metadata(self, tmp_path: Path):
        data_dir = tmp_path / "journals"
        data_dir.mkdir()
        (data_dir / "sjr_snapshot.csv").write_text(
            "full_name,abbr,quartile,acceptance_rate,h_index,topics,aliases,venue_type\n"
            "Test Journal,TJ,Q1,0.2,42,nlp|evaluation,Test Journal;TJ,journal\n",
            encoding="utf-8",
        )
        (data_dir / "conference_templates.yaml").write_text(
            yaml.dump(
                {
                    "conferences": [
                        {
                            "full_name": "Test Journal",
                            "abbr": "TJX",
                            "aliases": ["TJ Extra"],
                            "topic_keywords": ["agents"],
                        },
                        {
                            "full_name": "Brand New Conference",
                            "abbr": "BNC",
                            "aliases": ["BNC Alias"],
                            "topic_keywords": ["reasoning"],
                            "quartile": "Q1",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        recommender = JournalRecommender(data_dir)

        merged = next(
            item for item in recommender._candidates if item["full_name"] == "Test Journal"
        )
        added = next(
            item for item in recommender._candidates if item["full_name"] == "Brand New Conference"
        )
        assert merged["abbr"] == "TJX"
        assert "agents" in merged["topics"]
        assert "TJ Extra" in merged["aliases"]
        assert added["venue_type"] == "conference"

    def test_helper_methods_cover_edge_cases(self, recommender: JournalRecommender):
        assert recommender._extract_venue_name({}) == ""
        assert recommender._build_topic_query("9") == "artificial intelligence computer science"
        assert recommender._split_multi_value("") == []
        assert (
            recommender._name_similarity("pattern recognition", "Pattern Recognition Letters")
            >= 0.92
        )
        assert recommender._citation_fit_score({"aliases": ["NeurIPS"]}, {}) == 0.0
