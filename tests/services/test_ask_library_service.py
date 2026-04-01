# pyright: reportMissingImports=false

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from crane.services.ask_library_service import AskLibraryService
from crane.services.pdf_chunker import Chunk


@pytest.fixture
def service(service_refs_dir, monkeypatch: pytest.MonkeyPatch) -> AskLibraryService:
    monkeypatch.setattr(
        "crane.services.ask_library_service.list_paper_keys",
        lambda *_a, **_k: ["paper-a", "paper-b"],
    )
    monkeypatch.setattr(
        "crane.services.ask_library_service.read_paper_yaml",
        lambda _papers_dir, key: {"title": f"Title {key}"},
    )
    return AskLibraryService(refs_dir=service_refs_dir, embedding_api_key="embed-key")


def test_load_references_populates_memory(service: AskLibraryService) -> None:
    assert set(service._references.keys()) == {"paper-a", "paper-b"}


def test_embed_text_no_api_key_returns_none(
    service_refs_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("crane.services.ask_library_service.list_paper_keys", lambda *_a, **_k: [])
    monkeypatch.setattr(
        "crane.services.ask_library_service.read_paper_yaml", lambda *_a, **_k: None
    )
    svc = AskLibraryService(refs_dir=service_refs_dir, embedding_api_key=None)
    assert svc._embed_text("hello") is None


def test_embed_text_success_and_request_payload(
    service: AskLibraryService, mocked_requests_response: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mocked_requests_response.json.return_value = {"data": [{"embedding": [0.1, 0.2]}]}
    post = MagicMock(return_value=mocked_requests_response)
    monkeypatch.setattr("crane.services.ask_library_service.requests.post", post)

    out = service._embed_text("query text")
    assert out == [0.1, 0.2]
    post.assert_called_once_with(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": "Bearer embed-key", "Content-Type": "application/json"},
        json={"model": "text-embedding-3-small", "input": "query text"},
        timeout=30,
    )


def test_embed_text_exception_returns_none(
    service: AskLibraryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    post = MagicMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("crane.services.ask_library_service.requests.post", post)
    assert service._embed_text("q") is None


def test_retrieve_chunks_no_question_embedding_returns_empty(
    service: AskLibraryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "_embed_text", lambda *_a, **_k: None)
    assert service.retrieve_chunks("q") == []


def test_retrieve_chunks_no_chunks_returns_empty(
    service: AskLibraryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "_embed_text", lambda *_a, **_k: [1.0, 0.0])
    monkeypatch.setattr(service.chunker, "get_all_chunks", lambda: [])
    assert service.retrieve_chunks("q") == []


def test_retrieve_chunks_filters_by_paper_keys(
    service: AskLibraryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunks = [
        Chunk("c1", "paper-a", "aaa", 1, 0, 1),
        Chunk("c2", "paper-b", "bbb", 1, 2, 3),
    ]

    def fake_embed(text: str):
        return {
            "question": [1.0, 0.0],
            "aaa": [1.0, 0.0],
            "bbb": [0.0, 1.0],
        }.get(text, [1.0, 0.0])

    monkeypatch.setattr(service, "_embed_text", fake_embed)
    monkeypatch.setattr(service.chunker, "get_all_chunks", lambda: chunks)

    out = service.retrieve_chunks("question", k=5, paper_keys=["paper-a"])
    assert len(out) == 1
    assert out[0][0].paper_key == "paper-a"


def test_retrieve_chunks_skips_chunks_with_missing_embedding(
    service: AskLibraryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunks = [Chunk("c1", "paper-a", "aaa", 1, 0, 1), Chunk("c2", "paper-b", "bbb", 1, 2, 3)]

    def fake_embed(text: str):
        if text == "question":
            return [1.0, 0.0]
        if text == "aaa":
            return None
        return [0.0, 1.0]

    monkeypatch.setattr(service, "_embed_text", fake_embed)
    monkeypatch.setattr(service.chunker, "get_all_chunks", lambda: chunks)

    out = service.retrieve_chunks("question", k=3)
    assert len(out) == 1
    assert out[0][0].chunk_id == "c2"


def test_retrieve_chunks_returns_top_k_sorted(
    service: AskLibraryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunks = [
        Chunk("c1", "paper-a", "x", 1, 0, 1),
        Chunk("c2", "paper-a", "y", 1, 2, 3),
        Chunk("c3", "paper-b", "z", 1, 4, 5),
    ]
    vectors = {
        "question": [1.0, 0.0],
        "x": [1.0, 0.0],
        "y": [0.6, 0.8],
        "z": [0.0, 1.0],
    }
    monkeypatch.setattr(service, "_embed_text", lambda text: vectors[text])
    monkeypatch.setattr(service.chunker, "get_all_chunks", lambda: chunks)

    out = service.retrieve_chunks("question", k=2)
    assert [c.chunk_id for c, _ in out] == ["c1", "c2"]


def test_ask_returns_no_chunks_payload(
    service: AskLibraryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "retrieve_chunks", lambda **_k: [])
    out = service.ask("what?")
    assert out["status"] == "no_chunks"
    assert out["citations"] == []


def test_build_context_uses_reference_title_fallback(service: AskLibraryService) -> None:
    c1 = Chunk("1", "paper-a", "A text", 1, 0, 1)
    c2 = Chunk("2", "unknown", "B text", 2, 2, 3)
    context = service._build_context([(c1, 0.9), (c2, 0.8)])
    assert "Title paper-a" in context
    assert "unknown" in context


def test_ask_success_payload_with_citations(
    service: AskLibraryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    long_text = "x" * 220
    chunks = [(Chunk("1", "paper-a", long_text, 3, 0, 220), 0.91)]
    monkeypatch.setattr(service, "retrieve_chunks", lambda **_k: chunks)
    monkeypatch.setattr(service, "_synthesize_answer", lambda **_k: "final answer")

    out = service.ask("what is new?", k=1)
    assert out["status"] == "success"
    assert out["answer"] == "final answer"
    assert out["chunks_retrieved"] == 1
    assert out["citations"][0]["quote"].endswith("...")


def test_synthesize_answer_no_api_key_returns_message(service: AskLibraryService) -> None:
    out = service._synthesize_answer("q", "ctx", api_key=None)
    assert "requires OPENAI_API_KEY" in out


def test_synthesize_answer_calls_chat_completion(
    service: AskLibraryService,
    mocked_requests_response: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocked_requests_response.json.return_value = {
        "choices": [{"message": {"content": "Answer [1]"}}]
    }
    post = MagicMock(return_value=mocked_requests_response)
    monkeypatch.setattr("crane.services.ask_library_service.requests.post", post)

    out = service._synthesize_answer("question?", "context", api_key="chat-key")
    assert out == "Answer [1]"
    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "https://api.openai.com/v1/chat/completions"
    assert kwargs["headers"] == {
        "Authorization": "Bearer chat-key",
        "Content-Type": "application/json",
    }
    assert kwargs["json"]["model"] == "gpt-4o-mini"
    assert kwargs["timeout"] == 30


def test_synthesize_answer_exception_returns_error(
    service: AskLibraryService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "crane.services.ask_library_service.requests.post",
        MagicMock(side_effect=RuntimeError("network down")),
    )
    out = service._synthesize_answer("q", "ctx", api_key="k")
    assert out.startswith("Answer synthesis failed:")
