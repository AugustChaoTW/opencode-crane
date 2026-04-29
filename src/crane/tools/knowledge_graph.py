"""Knowledge graph tools: build and visualize paper knowledge graphs."""

from typing import Any

from crane.services.paper_knowledge_graph_service import PaperKnowledgeGraphService


def register_tools(mcp):
    """Register knowledge graph tools with the MCP server."""

    @mcp.tool()
    def build_paper_knowledge_graph(
        paper_path: str,
        force_rebuild: bool = False,
    ) -> dict[str, Any]:
        """Build a knowledge graph from a research paper.

        Parses the paper into sections, then extracts concepts and relationships
        from each section using LLM (with keyword-extraction fallback when no
        API key is available). Results are cached on disk; pass force_rebuild=True
        to regenerate even when the file has not changed.

        Args:
            paper_path:    Path to a .tex or .pdf paper file.
            force_rebuild: Force rebuild even if cache is valid.

        Returns:
            Dict with node count, edge count, and serialised graph data.
        """
        svc = PaperKnowledgeGraphService()
        kg = svc.build(paper_path, force_rebuild=force_rebuild)

        return {
            "status": "success",
            "paper_path": kg.paper_path,
            "file_hash": kg.file_hash,
            "node_count": len(kg.nodes),
            "edge_count": len(kg.edges),
            "nodes": {k: vars(v) for k, v in kg.nodes.items()},
            "edges": [vars(e) for e in kg.edges],
        }

    @mcp.tool()
    def visualize_knowledge_graph(
        paper_path: str,
        output_format: str = "mermaid",
    ) -> dict[str, Any]:
        """Visualize the paper knowledge graph.

        Loads (or builds) the knowledge graph for *paper_path* and renders it
        in the requested format.

        Args:
            paper_path:    Path to the paper file.
            output_format: Currently only "mermaid" is supported.

        Returns:
            Dict with the rendered diagram string and graph statistics.
        """
        svc = PaperKnowledgeGraphService()
        kg = svc.build(paper_path)

        if output_format == "mermaid":
            diagram = svc.to_mermaid(kg)
            return {
                "status": "success",
                "output_format": "mermaid",
                "diagram": diagram,
                "node_count": len(kg.nodes),
                "edge_count": len(kg.edges),
                "message": "Paste the diagram into mermaid.live or any Mermaid viewer.",
            }

        return {
            "status": "unsupported_format",
            "message": f"Unsupported output_format '{output_format}'. Use 'mermaid'.",
        }
