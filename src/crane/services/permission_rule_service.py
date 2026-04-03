from __future__ import annotations

import json
import importlib
import os
import re
from pathlib import Path
from typing import Any

import yaml

from crane.workspace import resolve_workspace

DEFAULT_PERMISSION_RULES = {
    "allow": [
        "Read files in the project directory",
        "Search the web for information",
        "List directory contents",
        "Search papers on arxiv",
    ],
    "soft_deny": [
        "Delete files",
        "Modify files outside of project directory",
        "Execute arbitrary shell commands",
        "Install packages",
    ],
    "environment": [
        "Default: user is interacting with CRANE research assistant",
    ],
}

CRITIQUE_SYSTEM_PROMPT = (
    "You are an expert reviewer of tool permission rules for an AI research assistant.\n"
    "\n"
    "The assistant has an 'auto mode' that uses an AI classifier to decide whether "
    "tool calls should be auto-approved or require user confirmation. Users can "
    "write custom rules in three categories:\n"
    "\n"
    "- **allow**: Actions the classifier should auto-approve\n"
    "- **soft_deny**: Actions the classifier should block (require user confirmation)\n"
    "- **environment**: Context about the user's setup that helps the classifier\n"
    "\n"
    "Your job is to critique the user's custom rules. For each rule, evaluate:\n"
    "1. **Clarity**: Is the rule unambiguous? Could the classifier misinterpret it?\n"
    "2. **Completeness**: Are there gaps or edge cases the rule doesn't cover?\n"
    "3. **Conflicts**: Do any of the rules conflict with each other?\n"
    "4. **Actionability**: Is the rule specific enough for the classifier to act on?\n"
    "\n"
    "Be concise and constructive. Only comment on rules that could be improved."
)


class PermissionRuleService:
    _VALID_CATEGORIES = ("allow", "soft_deny", "environment")

    def __init__(self, project_dir: str | None = None):
        workspace_root = self._resolve_project_root(project_dir)
        self.project_root = workspace_root
        self.config_path = Path(workspace_root) / ".crane" / "permissions.yaml"

    def add_rule(self, category: str, rule: str) -> dict[str, Any]:
        normalized_category = self._normalize_category(category)
        normalized_rule = rule.strip()
        if not normalized_rule:
            raise ValueError("rule must not be empty")

        rules = self._load_user_rules()
        category_rules = rules.setdefault(normalized_category, [])
        if normalized_rule not in category_rules:
            category_rules.append(normalized_rule)
            self._save_user_rules(rules)

        return {
            "ok": True,
            "category": normalized_category,
            "rule": normalized_rule,
            "count": len(category_rules),
        }

    def remove_rule(self, category: str, rule: str) -> dict[str, Any]:
        normalized_category = self._normalize_category(category)
        normalized_rule = rule.strip()

        rules = self._load_user_rules()
        category_rules = rules.setdefault(normalized_category, [])
        removed = False
        if normalized_rule in category_rules:
            category_rules.remove(normalized_rule)
            removed = True
            self._save_user_rules(rules)

        return {
            "ok": removed,
            "category": normalized_category,
            "rule": normalized_rule,
            "count": len(category_rules),
        }

    def list_rules(self) -> dict[str, list[str]]:
        return self._load_user_rules()

    def evaluate_action(self, action: str, context: dict | None = None) -> str:
        if not action.strip():
            return "deny"

        merged = self.show_effective_rules(dry_run=True)
        rules = merged.get("effective_rules", DEFAULT_PERMISSION_RULES)

        allow_match = self._matches_any_rule(action, rules.get("allow", []))
        soft_deny_match = self._matches_any_rule(action, rules.get("soft_deny", []))

        if allow_match:
            return "allow"

        environment_rules = rules.get("environment", [])
        permissive_env = self._is_permissive_environment(environment_rules, context)

        if soft_deny_match:
            return "allow" if permissive_env else "ask"

        if permissive_env:
            return "ask"

        return "deny"

    def merge_with_defaults(self, user_rules: dict | None = None) -> dict[str, list[str]]:
        source = user_rules if user_rules is not None else self._load_user_rules()
        merged: dict[str, list[str]] = {}

        for category in self._VALID_CATEGORIES:
            default_values = list(DEFAULT_PERMISSION_RULES.get(category, []))
            raw_user = source.get(category, []) if isinstance(source, dict) else []
            user_values = self._coerce_rule_list(raw_user)
            merged[category] = user_values if user_values else default_values

        return merged

    def show_effective_rules(self, dry_run: bool = False) -> dict[str, Any]:
        user_rules = self._load_user_rules()
        effective = self.merge_with_defaults(user_rules)
        has_custom_rules = any(bool(user_rules.get(cat)) for cat in self._VALID_CATEGORIES)
        return {
            "dry_run": dry_run,
            "config_path": str(self.config_path),
            "has_custom_rules": has_custom_rules,
            "user_rules": user_rules,
            "effective_rules": effective,
        }

    def critique_rules(
        self, rules: dict | None = None, model: str = "gpt-4o-mini"
    ) -> dict[str, Any]:
        custom_rules = rules if rules is not None else self._load_user_rules()
        normalized_rules = {
            cat: self._coerce_rule_list(custom_rules.get(cat, [])) for cat in self._VALID_CATEGORIES
        }
        has_custom_rules = any(normalized_rules.get(cat) for cat in self._VALID_CATEGORIES)

        if not has_custom_rules:
            return {
                "critique": "No custom rules found; defaults are in effect.",
                "issues_found": [],
                "overall_score": 10,
                "has_custom_rules": False,
            }

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "critique": "Skipped LLM critique: OPENAI_API_KEY is not set.",
                "issues_found": [],
                "overall_score": 0,
                "has_custom_rules": True,
            }

        try:
            openai_module = importlib.import_module("openai")
            OpenAI = getattr(openai_module, "OpenAI")
        except Exception:
            return {
                "critique": "Skipped LLM critique: openai package is unavailable.",
                "issues_found": [],
                "overall_score": 0,
                "has_custom_rules": True,
            }

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "permission_rule_critique",
                "schema": {
                    "type": "object",
                    "properties": {
                        "critique": {"type": "string"},
                        "issues_found": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "rule": {"type": "string"},
                                    "category": {
                                        "type": "string",
                                        "enum": [
                                            "clarity",
                                            "completeness",
                                            "conflict",
                                            "actionability",
                                        ],
                                    },
                                    "severity": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low"],
                                    },
                                    "suggestion": {"type": "string"},
                                },
                                "required": ["rule", "category", "severity", "suggestion"],
                                "additionalProperties": False,
                            },
                        },
                        "overall_score": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["critique", "issues_found", "overall_score"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }

        user_prompt = (
            "Review the following custom permission rules and return JSON only.\n\n"
            f"Rules:\n{json.dumps(normalized_rules, ensure_ascii=False, indent=2)}"
        )

        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_format,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
        except Exception as exc:
            return {
                "critique": f"LLM critique failed: {exc}",
                "issues_found": [],
                "overall_score": 0,
                "has_custom_rules": True,
            }

        return {
            "critique": str(parsed.get("critique", "")).strip(),
            "issues_found": parsed.get("issues_found", []),
            "overall_score": int(parsed.get("overall_score", 0) or 0),
            "has_custom_rules": True,
        }

    def _resolve_project_root(self, project_dir: str | None) -> str:
        try:
            workspace = resolve_workspace(project_dir)
            return workspace.project_root
        except Exception:
            if project_dir:
                return str(Path(project_dir).resolve())
            return str(Path.cwd())

    def _load_user_rules(self) -> dict[str, list[str]]:
        if not self.config_path.exists():
            return {category: [] for category in self._VALID_CATEGORIES}

        with self.config_path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}

        if not isinstance(raw, dict):
            return {category: [] for category in self._VALID_CATEGORIES}

        return {
            category: self._coerce_rule_list(raw.get(category, []))
            for category in self._VALID_CATEGORIES
        }

    def _save_user_rules(self, rules: dict[str, list[str]]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        normalized = {
            category: self._coerce_rule_list(rules.get(category, []))
            for category in self._VALID_CATEGORIES
        }
        with self.config_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(normalized, handle, sort_keys=False, allow_unicode=True)

    def _normalize_category(self, category: str) -> str:
        normalized = category.strip().lower()
        if normalized not in self._VALID_CATEGORIES:
            raise ValueError(
                f"invalid category '{category}', expected one of: {', '.join(self._VALID_CATEGORIES)}"
            )
        return normalized

    def _coerce_rule_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            rule = item.strip()
            if rule and rule not in normalized:
                normalized.append(rule)
        return normalized

    def _matches_any_rule(self, action: str, rules: list[str]) -> bool:
        normalized_action = self._normalize_text(action)
        return any(self._rule_matches_action(rule, normalized_action) for rule in rules)

    def _rule_matches_action(self, rule: str, normalized_action: str) -> bool:
        normalized_rule = self._normalize_text(rule)
        if not normalized_rule:
            return False

        if normalized_rule in normalized_action or normalized_action in normalized_rule:
            return True

        keywords = [
            token
            for token in normalized_rule.split()
            if len(token) >= 4 and token not in {"with", "that", "this", "from", "into", "outside"}
        ]
        if not keywords:
            return False

        matches = sum(1 for token in keywords if token in normalized_action)
        needed = 1 if len(keywords) <= 2 else max(2, len(keywords) // 2)
        return matches >= needed

    def _normalize_text(self, text: str) -> str:
        lowered = text.lower().strip()
        lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
        return " ".join(lowered.split())

    def _is_permissive_environment(
        self,
        environment_rules: list[str],
        context: dict | None = None,
    ) -> bool:
        context = context or {}
        if bool(context.get("expert_user")) or bool(context.get("trusted_user")):
            return True

        permissive_hints = ("expert user", "trusted user", "non-interactive", "ci mode")
        for rule in environment_rules:
            lowered = rule.lower()
            if any(hint in lowered for hint in permissive_hints):
                return True
        return False
