"""Integration tests for semantic search MCP tools."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.services.reference_service import ReferenceService
from crane.tools.semantic_search import register_tools


@pytest.fixture
def mock_mcp():
    """Create mock MCP server."""
    mcp = MagicMock()
    mcp.tool = lambda: lambda f: f
    return mcp


@pytest.fixture
def temp_refs_dir():
    """Create temporary references directory with sample data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        refs_path = Path(tmpdir) / "references"
        refs_path.mkdir(parents=True, exist_ok=True)

        ref_svc = ReferenceService(refs_path)
        ref_svc.add(
            key="paper1",
            title="Attention Is All You Need",
            authors=["Vaswani"],
            year=2017,
            abstract="We propose a new simple network architecture based on attention mechanisms.",
        )
        ref_svc.add(
            key="paper2",
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            authors=["Devlin"],
            year=2018,
            abstract="We introduce a new language representation model called BERT.",
        )

        embeddings_file = refs_path / "embeddings.yaml"
        embedding1 = [0.1] * 1536
        embedding2 = [0.2] * 1536

        import yaml

        data = {
            "embeddings": {
                "paper1": embedding1,
                "paper2": embedding2,
            },
            "metadata": {
                "model": "text-embedding-3-small",
                "embedding_count": 2,
                "last_updated": "2026-04-01T06:30:00Z",
            },
        }
        with open(embeddings_file, "w") as f:
            yaml.dump(data, f)

        yield refs_path


@pytest.fixture
def registered_tools(mock_mcp):
    """Register tools and capture them."""
    tools = {}

    def capture_tool(f):
        tools[f.__name__] = f
        return f

    mock_mcp.tool = lambda: capture_tool
    register_tools(mock_mcp)
    return tools


class TestSemanticSearchTool:
    """Test semantic_search MCP tool."""

    def test_semantic_search_returns_matches(self, registered_tools, temp_refs_dir):
        """Test that semantic_search returns matches when embeddings exist."""
        tool = registered_tools["semantic_search"]

        with (
            patch("os.getenv", return_value="test-key"),
            patch("crane.services.semantic_search_service.requests.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": [{"embedding": [0.1] * 1536}]}
            mock_post.return_value = mock_response

            result = tool(
                query="attention mechanism",
                k=2,
                refs_dir=str(temp_refs_dir),
                project_dir=None,
            )

        assert result["status"] == "success"
        assert "matches" in result
        assert isinstance(result["matches"], list)

    def test_semantic_search_respects_k_parameter(self, registered_tools, temp_refs_dir):
        """Test that semantic_search respects k parameter."""
        tool = registered_tools["semantic_search"]

        with patch("os.getenv", return_value="test-key"):
            result = tool(
                query="test",
                k=1,
                refs_dir=str(temp_refs_dir),
                project_dir=None,
            )

        assert len(result["matches"]) <= 1

    def test_semantic_search_returns_correct_schema(self, registered_tools, temp_refs_dir):
        """Test that results have correct schema."""
        tool = registered_tools["semantic_search"]

        with (
            patch("os.getenv", return_value="test-key"),
            patch("crane.services.semantic_search_service.requests.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": [{"embedding": [0.1] * 1536}]}
            mock_post.return_value = mock_response

            result = tool(
                query="test",
                k=5,
                refs_dir=str(temp_refs_dir),
                project_dir=None,
            )

        assert "query" in result
        assert "status" in result
        assert "match_count" in result
        assert "matches" in result

    def test_semantic_search_no_embeddings(self, registered_tools, temp_refs_dir):
        """Test semantic_search when embeddings don't exist."""
        empty_refs_dir = temp_refs_dir.parent / "empty_refs"
        empty_refs_dir.mkdir(exist_ok=True)
        ref_svc = ReferenceService(empty_refs_dir)
        ref_svc.add(key="test", title="Test", authors=["Author"], year=2024)

        tool = registered_tools["semantic_search"]

        with patch("os.getenv", return_value="test-key"):
            result = tool(
                query="test",
                k=5,
                refs_dir=str(empty_refs_dir),
                project_dir=None,
            )

        assert result["status"] == "no_embeddings"
        assert result["matches"] == []


class TestSemanticSearchByPaperTool:
    """Test semantic_search_by_paper MCP tool."""

    def test_search_by_paper_returns_matches(self, registered_tools, temp_refs_dir):
        """Test that semantic_search_by_paper returns matches."""
        tool = registered_tools["semantic_search_by_paper"]

        with patch("os.getenv", return_value="test-key"):
            result = tool(
                paper_key="paper1",
                k=5,
                refs_dir=str(temp_refs_dir),
                project_dir=None,
            )

        assert result["status"] == "success"
        assert "matches" in result

    def test_search_by_paper_excludes_itself(self, registered_tools, temp_refs_dir):
        """Test that results don't include the query paper."""
        tool = registered_tools["semantic_search_by_paper"]

        with patch("os.getenv", return_value="test-key"):
            result = tool(
                paper_key="paper1",
                k=5,
                refs_dir=str(temp_refs_dir),
                project_dir=None,
            )

        keys = [m["key"] for m in result["matches"]]
        assert "paper1" not in keys

    def test_search_by_paper_not_found(self, registered_tools, temp_refs_dir):
        """Test search_by_paper with nonexistent paper."""
        tool = registered_tools["semantic_search_by_paper"]

        with patch("os.getenv", return_value="test-key"):
            result = tool(
                paper_key="nonexistent",
                k=5,
                refs_dir=str(temp_refs_dir),
                project_dir=None,
            )

        assert result["status"] == "not_found"
        assert result["matches"] == []


class TestBuildEmbeddingsTool:
    """Test build_embeddings MCP tool."""

    def test_build_embeddings_requires_api_key(self, registered_tools, temp_refs_dir):
        """Test that build_embeddings fails without API key."""
        tool = registered_tools["build_embeddings"]

        with patch("os.getenv", return_value=None):
            result = tool(
                refs_dir=str(temp_refs_dir),
                project_dir=None,
            )

        assert result["status"] == "error"
        assert "OPENAI_API_KEY" in result["message"]

    def test_build_embeddings_returns_status(self, registered_tools, temp_refs_dir):
        """Test that build_embeddings returns proper status."""
        tool = registered_tools["build_embeddings"]

        with (
            patch("os.getenv", return_value="test-key"),
            patch("crane.services.semantic_search_service.requests.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": [{"embedding": [0.1] * 1536}]}
            mock_post.return_value = mock_response

            result = tool(
                refs_dir=str(temp_refs_dir),
                project_dir=None,
            )

        assert "status" in result
        assert "embedding_count" in result
        assert "cache_file" in result
