"""Ask My Library service for conversational Q&A over references."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import requests

from crane.services.pdf_chunker import Chunk, PDFChunker
from crane.services.semantic_search_service import SemanticSearchService
from crane.utils.yaml_io import list_paper_keys, read_paper_yaml


class AskLibraryService:
    """Service for answering questions about your reference library."""

    def __init__(
        self,
        refs_dir: str | Path = "references",
        embedding_api_key: str | None = None,
    ):
        self.refs_path = Path(refs_dir)
        self.papers_dir = self.refs_path / "papers"
        self.chunks_dir = self.refs_path / "chunks"

        self.embedding_api_key = embedding_api_key or os.getenv("OPENAI_API_KEY")
        self.chunker = PDFChunker(refs_dir=self.refs_path)
        self.semantic_svc = SemanticSearchService(
            refs_dir=self.refs_path,
            embedding_api_key=self.embedding_api_key,
        )

        self._references: dict[str, dict[str, Any]] = {}
        self._load_references()

    def _load_references(self) -> None:
        """Load all references into memory."""
        for key in list_paper_keys(str(self.papers_dir)):
            data = read_paper_yaml(str(self.papers_dir), key)
            if data:
                self._references[key] = data

    def _embed_text(self, text: str) -> list[float] | None:
        """Embed text using OpenAI API."""
        if not self.embedding_api_key:
            return None

        try:
            response = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.embedding_api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": "text-embedding-3-small", "input": text},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception:
            return None

    def retrieve_chunks(
        self,
        question: str,
        k: int = 5,
        paper_keys: list[str] | None = None,
    ) -> list[tuple[Chunk, float]]:
        """Retrieve most relevant chunks for a question.

        Args:
            question: Question to search for
            k: Number of chunks to return
            paper_keys: Optional filter to specific papers

        Returns:
            List of (Chunk, similarity_score) tuples
        """
        question_embedding = self._embed_text(question)
        if not question_embedding:
            return []

        all_chunks = self.chunker.get_all_chunks()
        if not all_chunks:
            return []

        if paper_keys:
            all_chunks = [c for c in all_chunks if c.paper_key in paper_keys]

        scored_chunks: list[tuple[Chunk, float]] = []
        query_vec = np.array(question_embedding, dtype=np.float32)

        for chunk in all_chunks:
            chunk_embedding = self._embed_text(chunk.text)
            if not chunk_embedding:
                continue

            chunk_vec = np.array(chunk_embedding, dtype=np.float32)
            similarity = float(
                np.dot(query_vec, chunk_vec)
                / (np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec) + 1e-8)
            )
            scored_chunks.append((chunk, similarity))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:k]

    def ask(
        self,
        question: str,
        k: int = 5,
        paper_keys: list[str] | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Answer a question using retrieved chunks.

        Args:
            question: Question to answer
            k: Number of chunks to retrieve
            paper_keys: Optional filter to specific papers
            api_key: OpenAI API key for answer synthesis

        Returns:
            Dict with answer, citations, and metadata
        """
        retrieved_chunks = self.retrieve_chunks(
            question=question,
            k=k,
            paper_keys=paper_keys,
        )

        if not retrieved_chunks:
            return {
                "status": "no_chunks",
                "message": "No chunks found. Run chunk_papers first or check PDFs exist.",
                "answer": "",
                "citations": [],
            }

        context = self._build_context(retrieved_chunks)
        answer = self._synthesize_answer(
            question=question,
            context=context,
            api_key=api_key or self.embedding_api_key,
        )

        citations = []
        for chunk, score in retrieved_chunks:
            ref = self._references.get(chunk.paper_key, {})
            citations.append(
                {
                    "paper_key": chunk.paper_key,
                    "title": ref.get("title", ""),
                    "page": chunk.page,
                    "quote": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                    "similarity": score,
                }
            )

        return {
            "status": "success",
            "question": question,
            "answer": answer,
            "citations": citations,
            "chunks_retrieved": len(retrieved_chunks),
        }

    def _build_context(self, chunks: list[tuple[Chunk, float]]) -> str:
        """Build context string from retrieved chunks."""
        lines = ["Based on the following excerpts from your library:\n"]

        for i, (chunk, score) in enumerate(chunks, 1):
            ref = self._references.get(chunk.paper_key, {})
            title = ref.get("title", chunk.paper_key)
            lines.append(f"[{i}] From '{title}' (Page {chunk.page}):\n{chunk.text}\n")

        return "\n".join(lines)

    def _synthesize_answer(
        self,
        question: str,
        context: str,
        api_key: str | None,
    ) -> str:
        """Synthesize answer from context using LLM."""
        if not api_key:
            return "Answer synthesis requires OPENAI_API_KEY. Showing retrieved chunks only."

        try:
            prompt = f"""You are a research assistant. Answer the following question using ONLY the provided excerpts from the researcher's library. Cite sources using [1], [2], etc. format. If the excerpts don't contain enough information to answer, say so.

{context}

Question: {question}

Answer:"""

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Answer synthesis failed: {e}"
