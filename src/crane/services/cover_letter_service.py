"""Cover Letter Generation Service - Create journal-specific cover letters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CoverLetterTemplate:
    journal_name: str
    opening: str
    scope_alignment: str
    contribution_statement: str
    closing: str
    tips: list[str]


class CoverLetterService:
    """Service for generating journal-specific cover letters."""

    JOURNAL_PROFILES = {
        "IEEE TPAMI": {
            "opening": "We are pleased to submit our manuscript for consideration in IEEE Transactions on Pattern Analysis and Machine Intelligence.",
            "scope_alignment": "This work directly addresses recent challenges in pattern analysis and machine intelligence, aligning with the journal's focus on methodological advances.",
            "contribution_emphasis": "methodological innovation",
            "tips": [
                "Emphasize pattern recognition and analysis contributions",
                "Highlight theoretical or practical novelty in methodology",
                "Reference related work in TPAMI",
                "Mention reproducibility and code availability",
            ],
        },
        "IJCV": {
            "opening": "We are pleased to submit our manuscript for consideration in the International Journal of Computer Vision.",
            "scope_alignment": "Our work advances the field of computer vision through novel approaches to visual understanding, directly aligned with IJCV's scope.",
            "contribution_emphasis": "computer vision breakthrough",
            "tips": [
                "Focus on visual understanding and perception",
                "Highlight benchmarking or dataset contributions",
                "Mention applications in real-world vision problems",
                "Include comprehensive experimental validation",
            ],
        },
        "NeurIPS": {
            "opening": "We are pleased to submit our manuscript for consideration in Neural Information Processing Systems.",
            "scope_alignment": "This work contributes to the core areas of NeurIPS, including machine learning, neural computation, and computational neuroscience.",
            "contribution_emphasis": "machine learning advancement",
            "tips": [
                "Emphasize novel algorithmic or theoretical contributions",
                "Highlight experimental rigor and statistical significance",
                "Mention implications for broader ML community",
                "Note any code or data release plans",
            ],
        },
        "ICML": {
            "opening": "We are pleased to submit our manuscript for consideration in the International Conference on Machine Learning.",
            "scope_alignment": "Our contributions address fundamental challenges in machine learning theory and practice, well-aligned with ICML's scope.",
            "contribution_emphasis": "machine learning innovation",
            "tips": [
                "Focus on algorithmic novelty or theoretical insights",
                "Demonstrate experimental advantage over baselines",
                "Include comprehensive ablation studies",
                "Highlight reproducibility (code, hyperparameters)",
            ],
        },
        "JMLR": {
            "opening": "We are pleased to submit our manuscript for consideration in the Journal of Machine Learning Research.",
            "scope_alignment": "This work contributes significant advances in machine learning research and methodology.",
            "contribution_emphasis": "machine learning research",
            "tips": [
                "Emphasize theoretical or practical soundness",
                "Include comprehensive experimental evaluation",
                "Discuss limitations and future work clearly",
                "Note open-source implementation availability",
            ],
        },
    }

    def generate_cover_letter(
        self,
        journal_name: str,
        paper_title: str = "",
        paper_highlights: list[str] | None = None,
        authors: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate journal-specific cover letter."""

        if paper_highlights is None:
            paper_highlights = [
                "Novel methodology",
                "Comprehensive experiments",
                "Strong empirical results",
            ]

        if authors is None:
            authors = ["The Authors"]

        profile = self.JOURNAL_PROFILES.get(journal_name)

        if profile:
            return self._generate_customized_letter(
                journal_name=journal_name,
                paper_title=paper_title,
                paper_highlights=paper_highlights,
                authors=authors,
                profile=profile,
            )

        return self._generate_generic_letter(
            journal_name=journal_name,
            paper_title=paper_title,
            paper_highlights=paper_highlights,
            authors=authors,
        )

    def _generate_customized_letter(
        self,
        journal_name: str,
        paper_title: str,
        paper_highlights: list[str],
        authors: list[str],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate customized cover letter based on journal profile."""

        highlights_text = "\n".join(f"• {h}" for h in paper_highlights)

        cover_letter = f"""{profile["opening"]}

Manuscript Title: {paper_title if paper_title else "[Your Paper Title]"}

{profile["scope_alignment"]}

Key Contributions:
{highlights_text}

The manuscript presents original research that contributes significantly to the field. 
We believe this work represents a strong {profile["contribution_emphasis"]} and will be of great 
interest to the {journal_name} readership.

We have ensured that:
• All experiments are reproducible with sufficient implementation details
• Data and code are available for verification
• The work complies with all ethical guidelines and standards
• Competing interests are disclosed (if applicable)
• No prior publication or concurrent submission to another venue exists

Thank you for considering our manuscript.

Sincerely,
{", ".join(authors)}
"""

        return {
            "status": "success",
            "journal_name": journal_name,
            "cover_letter": cover_letter,
            "tips": profile["tips"],
            "next_step": "Review the tips above and customize the letter with journal-specific details",
        }

    def _generate_generic_letter(
        self,
        journal_name: str,
        paper_title: str,
        paper_highlights: list[str],
        authors: list[str],
    ) -> dict[str, Any]:
        """Generate generic cover letter for unknown journal."""

        highlights_text = "\n".join(f"• {h}" for h in paper_highlights)

        cover_letter = f"""Dear Editor,

We are pleased to submit our manuscript for consideration in {journal_name}.

Manuscript Title: {paper_title if paper_title else "[Your Paper Title]"}

Key Contributions:
{highlights_text}

The manuscript presents original research that contributes significantly to the field. 
We believe it is a strong fit for your journal's scope and will be of great interest to your readers.

We have ensured that:
• All experiments are reproducible with sufficient implementation details
• Data and code are available for verification
• The work complies with all ethical guidelines and standards
• Competing interests are disclosed (if applicable)
• No prior publication or concurrent submission exists

Thank you for considering our manuscript.

Sincerely,
{", ".join(authors)}
"""

        return {
            "status": "success",
            "journal_name": journal_name,
            "cover_letter": cover_letter,
            "tips": [
                "Customize the opening to match the journal's specific focus",
                "Highlight contributions that align with the journal's scope",
                "Include the journal's specific submission guidelines",
                "Add journal-specific author instructions if available",
            ],
            "next_step": "Customize the cover letter with journal-specific details",
        }

    def get_supported_journals(self) -> dict[str, list[str]]:
        """Get list of supported journals and their customization tips."""
        return {
            "supported": list(self.JOURNAL_PROFILES.keys()),
            "custom_journals": "Any other journal name can be used - will generate generic template",
        }
