"""Citation graph tools: build graphs, find gaps, get clusters, visualize."""

from pathlib import Path
from typing import Any

from crane.services.citation_graph_service import CitationGraphService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    """Register citation graph tools with the MCP server."""

    def _resolve_refs_dir(refs_dir: str, project_dir: str | None) -> str:
        refs_path = Path(refs_dir)
        if refs_path.is_absolute():
            return str(refs_path)

        workspace = resolve_workspace(project_dir)
        if refs_path == Path("references"):
            return workspace.references_dir

        return str(Path(workspace.project_root) / refs_path)

    def _get_service(refs_dir: str, project_dir: str | None) -> CitationGraphService:
        resolved_dir = _resolve_refs_dir(refs_dir, project_dir)
        return CitationGraphService(refs_dir=resolved_dir)

    @mcp.tool()
    def build_citation_graph(
        source: str = "semantic_scholar",
        limit_per_paper: int = 10,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Build citation graph for all references.

        Fetches citation relationships from Semantic Scholar or OpenAlex
        and updates paper YAML files with cites/cited_by fields.

        Args:
            source:           Data source (semantic_scholar or openalex).
            limit_per_paper:  Max references to store per paper.
            refs_dir:         References directory path.
            project_dir:      Project root directory.

        Returns:
            Citation graph dict mapping paper keys to cited references.
        """
        service = _get_service(refs_dir, project_dir)
        graph = service.build_citation_graph(source=source, limit_per_paper=limit_per_paper)

        return {
            "status": "success",
            "source": source,
            "paper_count": len(graph),
            "graph": graph,
        }

    @mcp.tool()
    def find_citation_gaps(
        min_citation_count: int = 2,
        top_k: int = 20,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Find papers cited by multiple references but not in your library.

        These are likely important papers missing from your literature review.

        Args:
            min_citation_count: Min citations to be considered a gap.
            top_k:              Max gaps to return.
            refs_dir:           References directory path.
            project_dir:        Project root directory.

        Returns:
            List of missing papers with citation frequency.
        """
        service = _get_service(refs_dir, project_dir)
        gaps = service.find_citation_gaps(
            min_citation_count=min_citation_count,
            top_k=top_k,
        )

        return {
            "status": "success" if gaps else "no_gaps_found",
            "gap_count": len(gaps),
            "gaps": gaps,
            "message": (
                f"Found {len(gaps)} papers cited by {min_citation_count}+ of your "
                "references but missing from your library."
            ),
        }

    @mcp.tool()
    def get_research_clusters(
        k_clusters: int = 5,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Group references into topic clusters using semantic embeddings.

        Args:
            k_clusters:  Number of clusters to create.
            refs_dir:    References directory path.
            project_dir: Project root directory.

        Returns:
            List of clusters with paper keys and sizes.
        """
        service = _get_service(refs_dir, project_dir)
        clusters = service.get_research_clusters(k_clusters=k_clusters)

        if not clusters:
            return {
                "status": "no_embeddings",
                "message": "No embeddings found. Run build_embeddings first.",
                "clusters": [],
            }

        return {
            "status": "success",
            "cluster_count": len(clusters),
            "clusters": clusters,
        }

    @mcp.tool()
    def visualize_citations(
        mode: str = "graph",
        output_format: str = "mermaid",
        k_clusters: int = 5,
        output_path: str = "figures/citation_graph.pdf",
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Visualize citation relationships or research clusters.

        Consolidates get_citation_mermaid, get_cluster_mermaid, and
        visualize_citation_graph into a single tool.

        Args:
            mode:          "graph"    — citation relationships between papers.
                           "clusters" — topic cluster groupings (needs embeddings).
            output_format: "mermaid"  — Mermaid text (embed in Markdown / GitHub).
                           "figure"   — PDF/PNG file written to output_path
                                        (mode="graph" only).
            k_clusters:    Number of clusters (mode="clusters" only, default 5).
            output_path:   Destination file path (output_format="figure" only).
            refs_dir:      References directory path.
            project_dir:   Project root directory.

        Returns:
            Dict with mermaid string, or file path and stats for figure mode.
        """
        service = _get_service(refs_dir, project_dir)

        if mode == "clusters":
            mermaid = service.generate_cluster_mermaid(k_clusters=k_clusters)
            return {
                "status": "success",
                "mode": "clusters",
                "output_format": "mermaid",
                "mermaid": mermaid,
                "message": "Paste the mermaid string into any Mermaid viewer.",
            }

        # mode == "graph"
        if output_format == "figure":
            result = service.generate_citation_figure(output_path=output_path)
            if result["status"] == "success":
                result["message"] = (
                    f"Citation graph saved to {output_path}. "
                    f"{result['in_library']} in-library, {result['missing']} missing."
                )
            result["mode"] = "graph"
            result["output_format"] = "figure"
            return result

        # default: graph + mermaid
        mermaid = service.generate_citation_mermaid()
        return {
            "status": "success",
            "mode": "graph",
            "output_format": "mermaid",
            "mermaid": mermaid,
            "message": "Paste the mermaid string into any Mermaid viewer (GitHub, mermaid.live, etc.)",
        }
