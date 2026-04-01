"""PDF chunking service for splitting papers into retrievable passages."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
import re
from typing import Any

import yaml

PyPDF2 = import_module("PyPDF2")


@dataclass
class Chunk:
    """A chunk of text from a paper with page attribution."""

    chunk_id: str
    paper_key: str
    text: str
    page: int
    start_char: int
    end_char: int
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "chunk_id": self.chunk_id,
            "paper_key": self.paper_key,
            "text": self.text,
            "page": self.page,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chunk":
        """Deserialize from dict."""
        return cls(
            chunk_id=data["chunk_id"],
            paper_key=data["paper_key"],
            text=data["text"],
            page=data["page"],
            start_char=data["start_char"],
            end_char=data["end_char"],
        )


class PDFChunker:
    """Service for chunking PDF text into retrievable passages."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        refs_dir: str | Path = "references",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.refs_path = Path(refs_dir)
        self.chunks_dir = self.refs_path / "chunks"
        self.pdfs_dir = self.refs_path / "pdfs"

        self.chunks_dir.mkdir(parents=True, exist_ok=True)

    def chunk_pdf(
        self,
        paper_key: str,
        pdf_path: str | Path | None = None,
    ) -> list[Chunk]:
        """Chunk a PDF into passages with page attribution.

        Args:
            paper_key: Paper identifier
            pdf_path: Path to PDF. If None, looks in references/pdfs/

        Returns:
            List of Chunk objects
        """
        if pdf_path is None:
            pdf_path = self.pdfs_dir / f"{paper_key}.pdf"
        else:
            pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            return []

        reader = PyPDF2.PdfReader(str(pdf_path))

        all_chunks: list[Chunk] = []
        global_offset = 0

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                continue

            chunks = self._split_text(
                text=text,
                paper_key=paper_key,
                page=page_num,
                start_offset=global_offset,
            )
            all_chunks.extend(chunks)
            global_offset += len(text)

        return all_chunks

    def chunk_structured(self, paper_key: str, markdown_text: str) -> list[dict[str, Any]]:
        """Chunk structured markdown by section headings."""
        chunks: list[dict[str, Any]] = []
        sections = re.split(r"\n(?=## )", markdown_text)
        for index, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            lines = section.split("\n", 1)
            title = lines[0].lstrip("# ").strip()
            text = lines[1].strip() if len(lines) > 1 else ""
            if not text:
                continue

            chunks.append(
                {
                    "paper_key": paper_key,
                    "chunk_index": index,
                    "text": section,
                    "page": 0,
                    "section_title": title,
                    "word_count": len(text.split()),
                }
            )
        return chunks

    def _split_text(
        self,
        text: str,
        paper_key: str,
        page: int,
        start_offset: int,
    ) -> list[Chunk]:
        """Split text into overlapping chunks."""
        chunks: list[Chunk] = []
        words = text.split()

        if len(words) <= self.chunk_size:
            chunk_id = f"{paper_key}_p{page}_c0"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    paper_key=paper_key,
                    text=text.strip(),
                    page=page,
                    start_char=start_offset,
                    end_char=start_offset + len(text),
                )
            )
            return chunks

        start = 0
        chunk_idx = 0

        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_text = " ".join(words[start:end])

            chunk_id = f"{paper_key}_p{page}_c{chunk_idx}"

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    paper_key=paper_key,
                    text=chunk_text.strip(),
                    page=page,
                    start_char=start_offset + len(" ".join(words[:start])),
                    end_char=start_offset + len(" ".join(words[:end])),
                )
            )

            start += self.chunk_size - self.chunk_overlap
            chunk_idx += 1

        return chunks

    def save_chunks(self, paper_key: str, chunks: list[Chunk]) -> Path:
        """Save chunks to YAML file.

        Args:
            paper_key: Paper identifier
            chunks: List of chunks to save

        Returns:
            Path to saved chunks file
        """
        paper_chunks_dir = self.chunks_dir / paper_key
        paper_chunks_dir.mkdir(parents=True, exist_ok=True)

        output_file = paper_chunks_dir / "chunks.yaml"

        data = {
            "paper_key": paper_key,
            "chunk_count": len(chunks),
            "chunks": [chunk.to_dict() for chunk in chunks],
        }

        with open(output_file, "w") as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False)

        return output_file

    def load_chunks(self, paper_key: str) -> list[Chunk]:
        """Load chunks from YAML file.

        Args:
            paper_key: Paper identifier

        Returns:
            List of Chunk objects
        """
        chunks_file = self.chunks_dir / paper_key / "chunks.yaml"
        if not chunks_file.exists():
            return []

        with open(chunks_file) as f:
            data = yaml.safe_load(f)

        if not data or "chunks" not in data:
            return []

        return [Chunk.from_dict(c) for c in data["chunks"]]

    def chunk_and_save(
        self,
        paper_key: str,
        pdf_path: str | Path | None = None,
    ) -> int:
        """Chunk PDF and save to disk.

        Args:
            paper_key: Paper identifier
            pdf_path: Path to PDF

        Returns:
            Number of chunks created
        """
        chunks = self.chunk_pdf(paper_key, pdf_path)
        if chunks:
            self.save_chunks(paper_key, chunks)
        return len(chunks)

    def get_all_chunks(self) -> list[Chunk]:
        """Load all chunks from all papers.

        Returns:
            List of all Chunk objects
        """
        all_chunks: list[Chunk] = []

        for paper_dir in self.chunks_dir.iterdir():
            if paper_dir.is_dir():
                paper_key = paper_dir.name
                chunks = self.load_chunks(paper_key)
                all_chunks.extend(chunks)

        return all_chunks

    def get_stats(self) -> dict[str, Any]:
        """Get chunking statistics.

        Returns:
            Dict with stats
        """
        total_chunks = 0
        papers_chunked = 0

        for paper_dir in self.chunks_dir.iterdir():
            if paper_dir.is_dir():
                chunks_file = paper_dir / "chunks.yaml"
                if chunks_file.exists():
                    papers_chunked += 1
                    chunks = self.load_chunks(paper_dir.name)
                    total_chunks += len(chunks)

        return {
            "papers_chunked": papers_chunked,
            "total_chunks": total_chunks,
            "avg_chunks_per_paper": (total_chunks / papers_chunked if papers_chunked > 0 else 0),
        }
