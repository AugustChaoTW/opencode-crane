from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from crane.services.section_review_service import ReviewType
from crane.tools.section_review import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def test_review_paper_sections_uses_all_review_types_and_writes_yaml(tmp_path):
    collector = _ToolCollector()
    register_tools(collector)
    output_path = tmp_path / "reports" / "review.yaml"

    with (
        patch(
            "crane.tools.section_review.SectionReviewService.review_paper",
            return_value=object(),
        ) as review_mock,
        patch(
            "crane.tools.section_review.SectionReviewService.to_dict",
            return_value={"overall_score": 88},
        ),
    ):
        result = collector.tools["review_paper_sections"](
            paper_path="paper.tex",
            output_path=str(output_path),
        )

    assert result == {"overall_score": 88}
    assert output_path.exists()
    args = review_mock.call_args.args
    assert args[0] == "paper.tex"
    assert args[1] is None
    assert args[2] == list(ReviewType)


def test_review_paper_sections_converts_explicit_review_types():
    collector = _ToolCollector()
    register_tools(collector)

    with (
        patch(
            "crane.tools.section_review.SectionReviewService.review_paper",
            return_value=object(),
        ) as review_mock,
        patch(
            "crane.tools.section_review.SectionReviewService.to_dict",
            return_value={"overall_score": 90},
        ),
    ):
        collector.tools["review_paper_sections"](
            paper_path="paper.tex",
            sections=["Introduction"],
            review_types=[ReviewType.FRAMING.value],
        )

    args = review_mock.call_args.args
    assert args[1] == ["Introduction"]
    assert args[2] == [ReviewType.FRAMING]


def test_parse_paper_structure_returns_counts_and_truncated_abstract(tmp_path):
    collector = _ToolCollector()
    register_tools(collector)
    paper = tmp_path / "paper.tex"
    paper.write_text(
        "\\title{Test Paper}\n"
        "\\begin{abstract}\n" + ("A" * 240) + "\n\\end{abstract}\n"
        "\\section{Introduction}\nText\n"
        "\\appendix\n"
        "\\section{Appendix A}\nMore text\n",
        encoding="utf-8",
    )

    result = collector.tools["parse_paper_structure"](str(paper))

    assert result["title"] == "Test Paper"
    assert result["total_sections"] == 1
    assert result["total_appendices"] == 1
    assert result["abstract"].endswith("...")
