"""Ask My Library tools: conversational Q&A over references."""

from pathlib import Path
from typing import Any

from crane.services.ask_library_service import AskLibraryService
from crane.services.pdf_chunker import PDFChunker
from crane.workspace import resolve_workspace


def register_tools(mcp):
    """Register Ask My Library tools with the MCP server."""

    def _resolve_refs_dir(refs_dir: str, project_dir: str | None) -> str:
        refs_path = Path(refs_dir)
        if refs_path.is_absolute():
            return str(refs_path)

        workspace = resolve_workspace(project_dir)
        if refs_path == Path("references"):
            return workspace.references_dir

        return str(Path(workspace.project_root) / refs_path)

    @mcp.tool()
    def ask_library(
        question: str,
        k: int = 5,
        paper_keys: list[str] | None = None,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Ask a question about your reference library.

        Retrieves relevant passages from PDFs and synthesizes an answer
        with citations. Each citation includes paper key, title, page number,
        and quoted text.

        Args:
            question: Question to ask
            k: Number of passages to retrieve (default 5)
            paper_keys: Optional filter to specific papers
            refs_dir: References directory path
            project_dir: Project root directory

        Returns:
            Dict with answer, citations, and metadata
        """
        resolved_dir = _resolve_refs_dir(refs_dir, project_dir)
        service = AskLibraryService(refs_dir=resolved_dir)

        result = service.ask(
            question=question,
            k=k,
            paper_keys=paper_keys,
        )

        return result

    @mcp.tool()
    def chunk_papers(
        paper_keys: list[str] | None = None,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Chunk PDFs into retrievable passages.

        Splits each PDF into ~500-word passages with page attribution.
        Must be run before ask_library can retrieve chunks.

        Args:
            paper_keys: Specific papers to chunk (None = all)
            refs_dir: References directory path
            project_dir: Project root directory

        Returns:
            Dict with chunking stats
        """
        resolved_dir = _resolve_refs_dir(refs_dir, project_dir)
        chunker = PDFChunker(refs_dir=resolved_dir)

        if paper_keys is None:
            from crane.utils.yaml_io import list_paper_keys

            papers_dir = Path(resolved_dir) / "papers"
            paper_keys = list_paper_keys(str(papers_dir))

        total_chunks = 0
        papers_processed = 0
        errors = 0

        for key in paper_keys:
            try:
                count = chunker.chunk_and_save(key)
                total_chunks += count
                if count > 0:
                    papers_processed += 1
            except Exception:
                errors += 1

        return {
            "status": "success",
            "papers_processed": papers_processed,
            "total_chunks": total_chunks,
            "errors": errors,
            "message": f"Chunked {papers_processed} papers into {total_chunks} passages.",
        }

    @mcp.tool()
    def get_chunk_stats(
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Get statistics about chunked papers.

        Shows how many papers have been chunked and total chunk count.

        Args:
            refs_dir: References directory path
            project_dir: Project root directory

        Returns:
            Dict with chunking statistics
        """
        resolved_dir = _resolve_refs_dir(refs_dir, project_dir)
        chunker = PDFChunker(refs_dir=resolved_dir)
        stats = chunker.get_stats()

        return {
            "status": "success",
            **stats,
        }
