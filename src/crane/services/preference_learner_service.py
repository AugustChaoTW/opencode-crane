# pyright: reportMissingImports=false
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from crane.models.writing_style_models import (
    InteractiveRewriteSession,
    PreferenceLearnerState,
    RewriteChoice,
    RewriteSuggestion,
    UserPreference,
)

_CATEGORY_FOR_KEYWORD: dict[str, str] = {
    "passive": "grammar",
    "active voice": "grammar",
    "nominali": "grammar",
    "sentence": "readability",
    "readab": "readability",
    "complex": "readability",
    "simplif": "readability",
    "vocabul": "vocabulary",
    "jargon": "vocabulary",
    "technical": "vocabulary",
    "diversity": "vocabulary",
}

_METRIC_FOR_KEYWORD: dict[str, str] = {
    "passive": "passive_voice_ratio",
    "active voice": "passive_voice_ratio",
    "nominali": "nominalization_ratio",
    "sentence length": "avg_sentence_length",
    "sentence": "avg_sentence_length",
    "readab": "flesch_kincaid_grade",
    "complex": "flesch_kincaid_grade",
    "simplif": "flesch_kincaid_grade",
    "vocabul": "type_token_ratio",
    "jargon": "technical_term_density",
    "technical": "technical_term_density",
    "diversity": "type_token_ratio",
    "word length": "avg_word_length",
}


class PreferenceLearnerService:
    def __init__(self, storage_dir: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[3]
        self._storage_dir = Path(storage_dir) if storage_dir else root / "data" / "user_preferences"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def learn_from_session(
        self,
        session: InteractiveRewriteSession,
        user_id: str = "default",
    ) -> PreferenceLearnerState:
        state = self._load_state(user_id)

        for choice in session.choices:
            idx = self._parse_suggestion_index(choice.suggestion_id)
            if idx is None or idx >= len(session.suggestions):
                continue
            suggestion = session.suggestions[idx]
            self._update_preference(state, suggestion, choice)

        state.total_sessions += 1
        state.total_choices += len(session.choices)

        accepted = sum(1 for c in session.choices if c.decision == "accept")
        total = max(state.total_choices, 1)
        state.acceptance_rate = (
            accepted / total
            if state.total_choices == len(session.choices)
            else (
                (state.acceptance_rate * (state.total_choices - len(session.choices)) + accepted)
                / total
            )
        )

        state.updated_at = datetime.now(tz=timezone.utc).isoformat()
        self._save_state(state)
        return state

    def get_preference_weights(self, user_id: str = "default") -> dict[str, float]:
        state = self._load_state(user_id)
        weights: dict[str, float] = {}
        for metric_name, pref in state.preferences.items():
            sign = 1.0 if pref.direction == "higher" else -1.0
            weights[metric_name] = sign * pref.strength
        return weights

    def adjust_suggestions(
        self,
        suggestions: list[RewriteSuggestion],
        user_id: str = "default",
    ) -> list[RewriteSuggestion]:
        state = self._load_state(user_id)
        if not state.preferences:
            return suggestions

        adjusted: list[RewriteSuggestion] = []
        for sug in suggestions:
            boost = self._compute_preference_boost(sug, state)
            new_confidence = min(max(sug.confidence + boost, 0.0), 1.0)
            adjusted.append(
                RewriteSuggestion(
                    original_text=sug.original_text,
                    suggested_text=sug.suggested_text,
                    rationale=sug.rationale,
                    exemplar_source=sug.exemplar_source,
                    confidence=new_confidence,
                )
            )

        adjusted.sort(key=lambda s: -s.confidence)
        return adjusted

    def get_state(self, user_id: str = "default") -> PreferenceLearnerState:
        return self._load_state(user_id)

    def reset_preferences(self, user_id: str = "default") -> PreferenceLearnerState:
        state = PreferenceLearnerState(user_id=user_id)
        self._save_state(state)
        return state

    def get_preference_summary(self, user_id: str = "default") -> dict[str, Any]:
        state = self._load_state(user_id)
        prefs_summary: list[dict[str, Any]] = []
        for metric_name, pref in state.preferences.items():
            prefs_summary.append(
                {
                    "metric": metric_name,
                    "category": pref.category,
                    "direction": pref.direction,
                    "strength": round(pref.strength, 3),
                    "evidence_count": pref.evidence_count,
                }
            )
        prefs_summary.sort(key=lambda p: -p["strength"])

        return {
            "user_id": state.user_id,
            "total_sessions": state.total_sessions,
            "total_choices": state.total_choices,
            "acceptance_rate": round(state.acceptance_rate, 3),
            "preferences": prefs_summary,
            "category_weights": state.category_weights,
        }

    def _update_preference(
        self,
        state: PreferenceLearnerState,
        suggestion: RewriteSuggestion,
        choice: RewriteChoice,
    ) -> None:
        category, metric_name = self._infer_category_and_metric(suggestion)
        if not metric_name:
            return

        pref = state.preferences.get(metric_name)
        if pref is None:
            pref = UserPreference(
                category=category,
                metric_name=metric_name,
                direction="",
                strength=0.0,
                evidence_count=0,
            )

        direction = self._infer_direction(suggestion, choice)
        pref.evidence_count += 1

        if choice.decision == "accept":
            if not pref.direction:
                pref.direction = direction
            pref.strength = min(pref.strength + 0.1, 1.0)
        elif choice.decision == "reject":
            opposite = "lower" if direction == "higher" else "higher"
            if not pref.direction:
                pref.direction = opposite
            elif pref.direction == direction:
                pref.strength = max(pref.strength - 0.15, 0.0)
            else:
                pref.strength = min(pref.strength + 0.05, 1.0)
        elif choice.decision == "modify":
            if not pref.direction:
                pref.direction = direction
            pref.strength = min(pref.strength + 0.05, 1.0)

        pref.last_updated = datetime.now(tz=timezone.utc).isoformat()
        state.preferences[metric_name] = pref

        cat_weight = state.category_weights.get(category, 1.0)
        if choice.decision == "accept":
            cat_weight = min(cat_weight + 0.05, 2.0)
        elif choice.decision == "reject":
            cat_weight = max(cat_weight - 0.05, 0.5)
        state.category_weights[category] = round(cat_weight, 3)

    def _infer_category_and_metric(self, suggestion: RewriteSuggestion) -> tuple[str, str]:
        text = (suggestion.rationale + " " + suggestion.original_text).lower()
        for keyword, category in _CATEGORY_FOR_KEYWORD.items():
            if keyword in text:
                metric = _METRIC_FOR_KEYWORD.get(keyword, "")
                return category, metric
        return "readability", "flesch_kincaid_grade"

    @staticmethod
    def _infer_direction(suggestion: RewriteSuggestion, choice: RewriteChoice) -> str:
        text = suggestion.rationale.lower()
        lower_keywords = {"reduce", "lower", "decrease", "simplif", "shorter", "less"}
        higher_keywords = {"increase", "higher", "more", "longer", "complex", "precise"}

        for kw in lower_keywords:
            if kw in text:
                return "lower"
        for kw in higher_keywords:
            if kw in text:
                return "higher"
        return "lower"

    def _compute_preference_boost(
        self,
        suggestion: RewriteSuggestion,
        state: PreferenceLearnerState,
    ) -> float:
        category, metric_name = self._infer_category_and_metric(suggestion)
        pref = state.preferences.get(metric_name)
        if pref is None:
            return 0.0

        direction = self._infer_direction(suggestion, RewriteChoice())
        cat_weight = state.category_weights.get(category, 1.0)

        if pref.direction == direction:
            return pref.strength * 0.2 * cat_weight
        return -pref.strength * 0.1

    @staticmethod
    def _parse_suggestion_index(suggestion_id: str) -> int | None:
        parts = suggestion_id.split("_")
        if len(parts) >= 2:
            try:
                return int(parts[-1])
            except ValueError:
                return None
        return None

    def _load_state(self, user_id: str) -> PreferenceLearnerState:
        path = self._storage_dir / f"{user_id}.yaml"
        if not path.exists():
            return PreferenceLearnerState(user_id=user_id)

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return PreferenceLearnerState(user_id=user_id)

        preferences: dict[str, UserPreference] = {}
        for metric_name, pref_data in raw.get("preferences", {}).items():
            if isinstance(pref_data, dict):
                preferences[metric_name] = UserPreference(
                    category=pref_data.get("category", ""),
                    metric_name=pref_data.get("metric_name", metric_name),
                    direction=pref_data.get("direction", ""),
                    strength=float(pref_data.get("strength", 0.0)),
                    evidence_count=int(pref_data.get("evidence_count", 0)),
                    last_updated=pref_data.get("last_updated", ""),
                )

        return PreferenceLearnerState(
            user_id=raw.get("user_id", user_id),
            preferences=preferences,
            total_sessions=int(raw.get("total_sessions", 0)),
            total_choices=int(raw.get("total_choices", 0)),
            acceptance_rate=float(raw.get("acceptance_rate", 0.0)),
            category_weights=raw.get("category_weights", {}),
            created_at=raw.get("created_at", ""),
            updated_at=raw.get("updated_at", ""),
        )

    def _save_state(self, state: PreferenceLearnerState) -> None:
        prefs_data: dict[str, dict[str, Any]] = {}
        for metric_name, pref in state.preferences.items():
            prefs_data[metric_name] = {
                "category": pref.category,
                "metric_name": pref.metric_name,
                "direction": pref.direction,
                "strength": pref.strength,
                "evidence_count": pref.evidence_count,
                "last_updated": pref.last_updated,
            }

        data: dict[str, Any] = {
            "user_id": state.user_id,
            "preferences": prefs_data,
            "total_sessions": state.total_sessions,
            "total_choices": state.total_choices,
            "acceptance_rate": state.acceptance_rate,
            "category_weights": state.category_weights,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
        }
        path = self._storage_dir / f"{state.user_id}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
