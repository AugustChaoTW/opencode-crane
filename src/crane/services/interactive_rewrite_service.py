# pyright: reportMissingImports=false
from __future__ import annotations

import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from crane.models.writing_style_models import (
    InteractiveRewriteSession,
    RewriteChoice,
    RewriteSuggestion,
    SectionDiagnosis,
)
from crane.services.writing_style_service import WritingStyleService

_VALID_DECISIONS = {"accept", "reject", "modify"}


class InteractiveRewriteService:
    def __init__(self, storage_dir: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[3]
        self._storage_dir = Path(storage_dir) if storage_dir else root / "data" / "rewrite_sessions"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def start_session(
        self,
        paper_path: str,
        journal_name: str,
        section_name: str,
        max_suggestions: int = 5,
    ) -> InteractiveRewriteSession:
        service = WritingStyleService(journal_name)
        sections = service.section_chunker.chunk_latex_paper(paper_path)

        target = None
        for sec in sections:
            if (
                sec.canonical_name.lower() == section_name.lower()
                or sec.name.lower() == section_name.lower()
            ):
                target = sec
                break

        if target is None:
            raise ValueError(f"Section '{section_name}' not found in {paper_path}")

        diagnosis = service.diagnose_section(target)
        suggestions = service.suggest_rewrites(diagnosis, max_suggestions=max_suggestions)

        for i, sug in enumerate(suggestions):
            sug.exemplar_source = sug.exemplar_source or journal_name
            if not hasattr(sug, "_id"):
                object.__setattr__(sug, "_id", f"sug_{i}")

        session_id = f"rw_{int(time.time())}_{secrets.token_hex(4)}"
        session = InteractiveRewriteSession(
            session_id=session_id,
            paper_path=str(paper_path),
            journal_name=journal_name,
            section_name=section_name,
            suggestions=list(suggestions),
            choices=[],
            applied_rewrites=[],
            status="active",
        )
        self._save_session(session)
        return session

    def get_pending_suggestions(
        self, session: InteractiveRewriteSession
    ) -> list[RewriteSuggestion]:
        decided_indices = {
            int(c.suggestion_id.split("_")[-1])
            for c in session.choices
            if c.suggestion_id.startswith("sug_")
        }
        return [s for i, s in enumerate(session.suggestions) if i not in decided_indices]

    def submit_choice(
        self,
        session: InteractiveRewriteSession,
        suggestion_index: int,
        decision: str,
        modified_text: str = "",
        reason: str = "",
    ) -> InteractiveRewriteSession:
        if decision not in _VALID_DECISIONS:
            raise ValueError(f"Invalid decision '{decision}'. Must be one of: {_VALID_DECISIONS}")

        if suggestion_index < 0 or suggestion_index >= len(session.suggestions):
            raise IndexError(
                f"Suggestion index {suggestion_index} out of range (0-{len(session.suggestions) - 1})"
            )

        if decision == "modify" and not modified_text:
            raise ValueError("modified_text is required when decision is 'modify'")

        choice = RewriteChoice(
            suggestion_id=f"sug_{suggestion_index}",
            decision=decision,
            modified_text=modified_text,
            reason=reason,
        )
        session.choices.append(choice)

        suggestion = session.suggestions[suggestion_index]
        if decision == "accept":
            session.applied_rewrites.append(suggestion)
        elif decision == "modify":
            modified_suggestion = RewriteSuggestion(
                original_text=suggestion.original_text,
                suggested_text=modified_text,
                rationale=suggestion.rationale,
                exemplar_source=suggestion.exemplar_source,
                confidence=suggestion.confidence,
            )
            session.applied_rewrites.append(modified_suggestion)

        session.updated_at = datetime.now(tz=timezone.utc).isoformat()

        if len(session.choices) >= len(session.suggestions):
            session.status = "completed"

        self._save_session(session)
        return session

    def get_session_summary(self, session: InteractiveRewriteSession) -> dict[str, Any]:
        accepted = sum(1 for c in session.choices if c.decision == "accept")
        rejected = sum(1 for c in session.choices if c.decision == "reject")
        modified = sum(1 for c in session.choices if c.decision == "modify")
        total = len(session.choices)

        return {
            "session_id": session.session_id,
            "paper_path": session.paper_path,
            "journal_name": session.journal_name,
            "section_name": session.section_name,
            "status": session.status,
            "total_suggestions": len(session.suggestions),
            "decisions_made": total,
            "accepted": accepted,
            "rejected": rejected,
            "modified": modified,
            "acceptance_rate": accepted / max(total, 1),
            "applied_count": len(session.applied_rewrites),
        }

    def pause_session(self, session: InteractiveRewriteSession) -> InteractiveRewriteSession:
        session.status = "paused"
        session.updated_at = datetime.now(tz=timezone.utc).isoformat()
        self._save_session(session)
        return session

    def resume_session(self, session_id: str) -> InteractiveRewriteSession:
        session = self._load_session(session_id)
        if session.status == "completed":
            raise ValueError(f"Session {session_id} is already completed")
        session.status = "active"
        session.updated_at = datetime.now(tz=timezone.utc).isoformat()
        self._save_session(session)
        return session

    def list_sessions(self, status: str = "") -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for path in sorted(self._storage_dir.glob("*.yaml")):
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    continue
                if status and raw.get("status") != status:
                    continue
                results.append(
                    {
                        "session_id": raw.get("session_id", path.stem),
                        "paper_path": raw.get("paper_path", ""),
                        "journal_name": raw.get("journal_name", ""),
                        "section_name": raw.get("section_name", ""),
                        "status": raw.get("status", "unknown"),
                        "decisions_made": len(raw.get("choices", [])),
                        "total_suggestions": len(raw.get("suggestions", [])),
                    }
                )
            except (yaml.YAMLError, OSError):
                continue
        return results

    def _save_session(self, session: InteractiveRewriteSession) -> None:
        data: dict[str, Any] = {
            "session_id": session.session_id,
            "paper_path": session.paper_path,
            "journal_name": session.journal_name,
            "section_name": session.section_name,
            "status": session.status,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "suggestions": [
                {
                    "original_text": s.original_text,
                    "suggested_text": s.suggested_text,
                    "rationale": s.rationale,
                    "exemplar_source": s.exemplar_source,
                    "confidence": s.confidence,
                }
                for s in session.suggestions
            ],
            "choices": [
                {
                    "suggestion_id": c.suggestion_id,
                    "decision": c.decision,
                    "modified_text": c.modified_text,
                    "reason": c.reason,
                    "timestamp": c.timestamp,
                }
                for c in session.choices
            ],
            "applied_rewrites": [
                {
                    "original_text": s.original_text,
                    "suggested_text": s.suggested_text,
                    "rationale": s.rationale,
                    "exemplar_source": s.exemplar_source,
                    "confidence": s.confidence,
                }
                for s in session.applied_rewrites
            ],
        }
        path = self._storage_dir / f"{session.session_id}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def _load_session(self, session_id: str) -> InteractiveRewriteSession:
        path = self._storage_dir / f"{session_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid session file: {session_id}")

        suggestions = [
            RewriteSuggestion(
                original_text=s.get("original_text", ""),
                suggested_text=s.get("suggested_text", ""),
                rationale=s.get("rationale", ""),
                exemplar_source=s.get("exemplar_source", ""),
                confidence=float(s.get("confidence", 0.0)),
            )
            for s in raw.get("suggestions", [])
        ]

        choices = [
            RewriteChoice(
                suggestion_id=c.get("suggestion_id", ""),
                decision=c.get("decision", "accept"),
                modified_text=c.get("modified_text", ""),
                reason=c.get("reason", ""),
                timestamp=c.get("timestamp", ""),
            )
            for c in raw.get("choices", [])
        ]

        applied = [
            RewriteSuggestion(
                original_text=s.get("original_text", ""),
                suggested_text=s.get("suggested_text", ""),
                rationale=s.get("rationale", ""),
                exemplar_source=s.get("exemplar_source", ""),
                confidence=float(s.get("confidence", 0.0)),
            )
            for s in raw.get("applied_rewrites", [])
        ]

        return InteractiveRewriteSession(
            session_id=raw.get("session_id", session_id),
            paper_path=raw.get("paper_path", ""),
            journal_name=raw.get("journal_name", ""),
            section_name=raw.get("section_name", ""),
            suggestions=suggestions,
            choices=choices,
            applied_rewrites=applied,
            status=raw.get("status", "active"),
            created_at=raw.get("created_at", ""),
            updated_at=raw.get("updated_at", ""),
        )
