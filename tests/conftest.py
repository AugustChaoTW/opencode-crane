"""
Shared fixtures for opencode-crane TDD tests.

Provides:
- Temporary references/ directory structure
- Mock gh CLI subprocess responses
- Mock git subprocess responses
- Sample paper data
- Sample YAML / BibTeX content
"""

import json
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Temporary filesystem fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with references/ structure."""
    refs = tmp_path / "references"
    papers = refs / "papers"
    pdfs = refs / "pdfs"
    papers.mkdir(parents=True)
    pdfs.mkdir(parents=True)
    (refs / "bibliography.bib").write_text("", encoding="utf-8")
    return tmp_path


@pytest.fixture
def refs_dir(tmp_project):
    """Shortcut to references/ directory."""
    return str(tmp_project / "references")


@pytest.fixture
def papers_dir(tmp_project):
    """Shortcut to references/papers/ directory."""
    return str(tmp_project / "references" / "papers")


@pytest.fixture
def bib_path(tmp_project):
    """Shortcut to references/bibliography.bib path."""
    return str(tmp_project / "references" / "bibliography.bib")


# ---------------------------------------------------------------------------
# Sample paper data
# ---------------------------------------------------------------------------

SAMPLE_PAPER_DICT = {
    "key": "vaswani2017-attention",
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
    "year": 2017,
    "doi": "10.48550/arXiv.1706.03762",
    "venue": "NeurIPS",
    "url": "https://arxiv.org/abs/1706.03762",
    "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
    "abstract": (
        "The dominant sequence transduction models are based on complex"
        " recurrent or convolutional neural networks."
    ),
    "source": "arxiv",
    "paper_type": "conference",
    "categories": ["cs.CL", "cs.AI"],
    "keywords": ["transformer", "attention", "sequence-to-sequence"],
}

SAMPLE_PAPER_DICT_2 = {
    "key": "brown2020-gpt3",
    "title": "Language Models are Few-Shot Learners",
    "authors": ["Tom Brown", "Benjamin Mann", "Nick Ryder"],
    "year": 2020,
    "doi": "10.48550/arXiv.2005.14165",
    "venue": "NeurIPS",
    "url": "https://arxiv.org/abs/2005.14165",
    "pdf_url": "https://arxiv.org/pdf/2005.14165.pdf",
    "abstract": (
        "We demonstrate that scaling up language models greatly improves"
        " task-agnostic, few-shot performance."
    ),
    "source": "arxiv",
    "paper_type": "conference",
    "categories": ["cs.CL"],
    "keywords": ["gpt", "language-model", "few-shot"],
}

SAMPLE_BIBTEX_ENTRY = """@inproceedings{vaswani2017-attention,
  title={Attention Is All You Need},
  author={Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
  booktitle={NeurIPS},
  year={2017},
  doi={10.48550/arXiv.1706.03762}
}"""


@pytest.fixture
def sample_paper_dict():
    """Return a copy of sample paper data."""
    return SAMPLE_PAPER_DICT.copy()


@pytest.fixture
def sample_paper_dict_2():
    """Return a copy of second sample paper data."""
    return SAMPLE_PAPER_DICT_2.copy()


@pytest.fixture
def sample_bibtex():
    """Return sample BibTeX entry string."""
    return SAMPLE_BIBTEX_ENTRY


# ---------------------------------------------------------------------------
# Mock gh CLI
# ---------------------------------------------------------------------------


class MockGhCli:
    """Mock for gh CLI subprocess calls. Records calls and returns preset responses."""

    def __init__(self):
        self.calls: list[list[str]] = []
        self.responses: dict[str, str] = {}
        self.default_response = ""

    def set_response(self, subcommand: str, response: str):
        """Set response for a subcommand pattern (e.g. 'issue create')."""
        self.responses[subcommand] = response

    def run(self, cmd, **kwargs):
        """Mock subprocess.run for gh commands."""
        self.calls.append(cmd)
        cmd_str = " ".join(cmd[1:3]) if len(cmd) >= 3 else " ".join(cmd[1:])
        stdout = self.responses.get(cmd_str, self.default_response)
        mock_result = MagicMock()
        mock_result.stdout = stdout
        mock_result.stderr = ""
        mock_result.returncode = 0
        return mock_result


@pytest.fixture
def mock_gh():
    """Provide a MockGhCli instance with common preset responses."""
    gh = MockGhCli()
    gh.set_response(
        "issue create",
        json.dumps({"number": 1, "url": "https://github.com/test/repo/issues/1"}),
    )
    gh.set_response(
        "issue list",
        json.dumps(
            [
                {
                    "number": 1,
                    "title": "[LIT] Survey of X",
                    "state": "open",
                    "labels": [{"name": "phase:literature-review"}],
                },
            ]
        ),
    )
    gh.set_response(
        "issue view",
        json.dumps(
            {
                "number": 1,
                "title": "[LIT] Survey of X",
                "body": "task body",
                "state": "open",
                "comments": [],
            }
        ),
    )
    gh.set_response("issue edit", "")
    gh.set_response("issue comment", "")
    gh.set_response("issue close", "")
    gh.set_response("label create", "")
    return gh


# ---------------------------------------------------------------------------
# Mock git
# ---------------------------------------------------------------------------


class MockGitInfo:
    """Mock for git subprocess calls."""

    def __init__(self, owner="testuser", repo="test-research", branch="main"):
        self.owner = owner
        self.repo = repo
        self.branch = branch

    def run(self, cmd, **kwargs):
        cmd_str = " ".join(cmd)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        if "remote get-url" in cmd_str:
            mock_result.stdout = f"git@github.com:{self.owner}/{self.repo}.git\n"
        elif "rev-parse --abbrev-ref" in cmd_str:
            mock_result.stdout = f"{self.branch}\n"
        elif "rev-parse --show-toplevel" in cmd_str:
            mock_result.stdout = "/tmp/test-project\n"
        elif "log -1" in cmd_str:
            mock_result.stdout = "abc1234 initial commit\n"
        else:
            mock_result.stdout = "\n"
        return mock_result


@pytest.fixture
def mock_git():
    """Provide a MockGitInfo instance."""
    return MockGitInfo()


# ---------------------------------------------------------------------------
# Mock arXiv API
# ---------------------------------------------------------------------------

SAMPLE_ARXIV_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All You Need</title>
    <summary>Dominant sequence transduction models use complex recurrent networks.</summary>
    <published>2017-06-12T00:00:00Z</published>
    <updated>2023-08-02T00:00:00Z</updated>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <link href="http://arxiv.org/pdf/1706.03762v7" type="application/pdf"/>
    <category term="cs.CL"/>
    <category term="cs.AI"/>
  </entry>
</feed>"""


@pytest.fixture
def mock_arxiv_response():
    """Return sample arXiv API XML response."""
    return SAMPLE_ARXIV_RESPONSE
