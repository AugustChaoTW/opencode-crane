from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from crane.services.pdf_chunker import Chunk, PDFChunker


@pytest.fixture
def chunker(service_refs_dir: Path) -> PDFChunker:
    return PDFChunker(chunk_size=5, chunk_overlap=1, refs_dir=service_refs_dir)


def test_chunk_to_dict_and_from_dict_roundtrip() -> None:
    chunk = Chunk("id", "paper", "text", 1, 0, 4)
    restored = Chunk.from_dict(chunk.to_dict())
    assert restored == chunk


def test_chunk_pdf_returns_empty_when_missing_pdf(chunker: PDFChunker) -> None:
    assert chunker.chunk_pdf("p1") == []


def test_chunk_pdf_skips_empty_pages(
    chunker: PDFChunker, monkeypatch: pytest.MonkeyPatch, service_refs_dir: Path
) -> None:
    pdf = service_refs_dir / "pdfs" / "p1.pdf"
    pdf.write_bytes(b"pdf")

    page1 = MagicMock()
    page1.extract_text.return_value = ""
    page2 = MagicMock()
    page2.extract_text.return_value = "a b c d e"
    mock_reader = MagicMock()
    mock_reader.pages = [page1, page2]
    monkeypatch.setattr(
        "crane.services.pdf_chunker.PyPDF2.PdfReader", lambda *_a, **_k: mock_reader
    )

    chunks = chunker.chunk_pdf("p1")
    assert len(chunks) == 1
    assert chunks[0].page == 2


def test_chunk_pdf_custom_pdf_path(
    chunker: PDFChunker, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"pdf")
    page = MagicMock()
    page.extract_text.return_value = "one two three"
    reader = MagicMock()
    reader.pages = [page]
    monkeypatch.setattr("crane.services.pdf_chunker.PyPDF2.PdfReader", lambda *_a, **_k: reader)

    out = chunker.chunk_pdf("p2", pdf_path=pdf)
    assert len(out) == 1
    assert out[0].chunk_id.startswith("p2_p1_c")


def test_split_text_single_chunk_when_short(chunker: PDFChunker) -> None:
    chunks = chunker._split_text("a b c", paper_key="p1", page=1, start_offset=10)
    assert len(chunks) == 1
    assert chunks[0].start_char == 10
    assert chunks[0].end_char == 15


def test_split_text_overlapping_chunks(chunker: PDFChunker) -> None:
    text = "one two three four five six seven eight nine"
    chunks = chunker._split_text(text, paper_key="p1", page=1, start_offset=0)
    assert len(chunks) >= 2
    assert chunks[0].chunk_id == "p1_p1_c0"
    assert chunks[1].chunk_id == "p1_p1_c1"
    assert chunks[1].start_char < chunks[0].end_char


@pytest.mark.parametrize("start_offset", [0, 5, 20])
def test_split_text_respects_start_offset(chunker: PDFChunker, start_offset: int) -> None:
    chunks = chunker._split_text("a b c d e f g", "p1", 3, start_offset)
    assert chunks[0].start_char >= start_offset


def test_save_and_load_chunks_roundtrip(chunker: PDFChunker) -> None:
    chunks = [Chunk("id1", "p1", "text", 1, 0, 4)]
    out_path = chunker.save_chunks("p1", chunks)
    assert out_path.exists()
    loaded = chunker.load_chunks("p1")
    assert len(loaded) == 1
    assert loaded[0].chunk_id == "id1"


def test_load_chunks_missing_file_returns_empty(chunker: PDFChunker) -> None:
    assert chunker.load_chunks("missing") == []


def test_load_chunks_handles_invalid_yaml_payload(
    chunker: PDFChunker, service_refs_dir: Path
) -> None:
    target = chunker.chunks_dir / "p1"
    target.mkdir(parents=True)
    (target / "chunks.yaml").write_text("foo: bar", encoding="utf-8")
    assert chunker.load_chunks("p1") == []


def test_chunk_and_save_saves_when_chunks_exist(
    chunker: PDFChunker, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunks = [Chunk("id", "p1", "t", 1, 0, 1)]
    save_mock = MagicMock()
    monkeypatch.setattr(chunker, "chunk_pdf", lambda *_a, **_k: chunks)
    monkeypatch.setattr(chunker, "save_chunks", save_mock)

    count = chunker.chunk_and_save("p1")
    assert count == 1
    save_mock.assert_called_once_with("p1", chunks)


def test_chunk_and_save_no_save_when_empty(
    chunker: PDFChunker, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_mock = MagicMock()
    monkeypatch.setattr(chunker, "chunk_pdf", lambda *_a, **_k: [])
    monkeypatch.setattr(chunker, "save_chunks", save_mock)
    assert chunker.chunk_and_save("p1") == 0
    save_mock.assert_not_called()


def test_get_all_chunks_reads_each_paper_dir(chunker: PDFChunker) -> None:
    chunker.save_chunks("p1", [Chunk("1", "p1", "a", 1, 0, 1)])
    chunker.save_chunks("p2", [Chunk("2", "p2", "b", 1, 0, 1)])
    all_chunks = chunker.get_all_chunks()
    assert {c.paper_key for c in all_chunks} == {"p1", "p2"}


def test_get_stats_no_chunks(chunker: PDFChunker) -> None:
    stats = chunker.get_stats()
    assert stats["papers_chunked"] == 0
    assert stats["avg_chunks_per_paper"] == 0


def test_get_stats_with_saved_chunks(chunker: PDFChunker) -> None:
    chunker.save_chunks("p1", [Chunk("1", "p1", "a", 1, 0, 1), Chunk("2", "p1", "b", 1, 1, 2)])
    chunker.save_chunks("p2", [Chunk("3", "p2", "c", 2, 0, 1)])
    stats = chunker.get_stats()
    assert stats["papers_chunked"] == 2
    assert stats["total_chunks"] == 3
    assert stats["avg_chunks_per_paper"] == 1.5
