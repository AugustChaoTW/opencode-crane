# pyright: reportMissingImports=false

from __future__ import annotations

import json
import types

import pytest
import yaml

from crane.services.permission_rule_service import DEFAULT_PERMISSION_RULES, PermissionRuleService


class _Workspace:
    def __init__(self, project_root: str):
        self.project_root = project_root


def _make_service(tmp_path, monkeypatch) -> PermissionRuleService:
    monkeypatch.setattr(
        "crane.services.permission_rule_service.resolve_workspace",
        lambda project_dir: _Workspace(str(tmp_path)),
    )
    return PermissionRuleService(project_dir=str(tmp_path))


def test_init_uses_workspace_root_for_config_path(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    assert service.config_path == tmp_path / ".crane" / "permissions.yaml"


def test_add_rule_persists_and_deduplicates(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)

    first = service.add_rule("allow", "Read docs in project")
    second = service.add_rule("allow", "Read docs in project")

    assert first["ok"] is True
    assert second["count"] == 1
    payload = yaml.safe_load(service.config_path.read_text(encoding="utf-8"))
    assert payload["allow"] == ["Read docs in project"]


def test_add_rule_invalid_category_raises(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="invalid category"):
        service.add_rule("deny", "block all")


def test_remove_rule_returns_false_when_missing(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    result = service.remove_rule("soft_deny", "Delete files")
    assert result["ok"] is False


def test_remove_rule_removes_existing_entry(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("soft_deny", "Delete files")

    result = service.remove_rule("soft_deny", "Delete files")
    assert result["ok"] is True
    assert service.list_rules()["soft_deny"] == []


def test_merge_with_defaults_uses_replace_per_category(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    user_rules = {
        "allow": ["Only this allow rule"],
        "soft_deny": [],
        "environment": ["expert user"],
    }

    merged = service.merge_with_defaults(user_rules)

    assert merged["allow"] == ["Only this allow rule"]
    assert merged["soft_deny"] == DEFAULT_PERMISSION_RULES["soft_deny"]
    assert merged["environment"] == ["expert user"]


def test_show_effective_rules_reports_custom_state(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    before = service.show_effective_rules(dry_run=True)
    assert before["has_custom_rules"] is False

    service.add_rule("allow", "Read files in project")
    after = service.show_effective_rules(dry_run=False)
    assert after["has_custom_rules"] is True
    assert after["dry_run"] is False


def test_evaluate_action_allow_precedence_over_soft_deny(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("allow", "install packages")
    service.add_rule("soft_deny", "install packages")

    decision = service.evaluate_action("Please install packages for this repo")
    assert decision == "allow"


def test_evaluate_action_soft_deny_returns_ask(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    decision = service.evaluate_action("Delete files in workspace")
    assert decision == "ask"


def test_evaluate_action_unknown_defaults_to_deny(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    decision = service.evaluate_action("Reboot remote machine")
    assert decision == "deny"


def test_evaluate_action_permissive_context_upgrades_unknown_to_ask(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    decision = service.evaluate_action("Reboot remote machine", context={"expert_user": True})
    assert decision == "ask"


def test_evaluate_action_permissive_environment_upgrades_soft_deny_to_allow(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("environment", "User is expert user and trusted user")
    decision = service.evaluate_action("Execute arbitrary shell commands for diagnostics")
    assert decision == "allow"


def test_critique_rules_without_custom_rules_returns_default_message(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    result = service.critique_rules()
    assert result["has_custom_rules"] is False
    assert result["overall_score"] == 10


def test_critique_rules_without_api_key_skips_gracefully(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("allow", "Read files in the project directory")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = service.critique_rules()
    assert "OPENAI_API_KEY" in result["critique"]
    assert result["has_custom_rules"] is True


def test_critique_rules_handles_openai_import_error(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("allow", "Read files in the project directory")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    original_import = __import__

    def _raising_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "openai":
            raise ImportError("missing openai")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", _raising_import)

    result = service.critique_rules()
    assert "openai package is unavailable" in result["critique"]
    assert result["overall_score"] == 0


def test_critique_rules_returns_parsed_llm_payload(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("allow", "Read files in the project directory")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    payload = {
        "critique": "Rules are mostly clear; tighten shell scope.",
        "issues_found": [
            {
                "rule": "Read files in the project directory",
                "category": "actionability",
                "severity": "low",
                "suggestion": "Specify allowed file patterns.",
            }
        ],
        "overall_score": 8,
    }

    class _Completions:
        @staticmethod
        def create(**kwargs):
            content = json.dumps(payload)
            message = types.SimpleNamespace(content=content)
            choice = types.SimpleNamespace(message=message)
            return types.SimpleNamespace(choices=[choice])

    class _Chat:
        completions = _Completions()

    class _Client:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.chat = _Chat()

    monkeypatch.setitem(__import__("sys").modules, "openai", types.SimpleNamespace(OpenAI=_Client))

    result = service.critique_rules(model="gpt-4o-mini")
    assert result["overall_score"] == 8
    assert result["issues_found"][0]["category"] == "actionability"
    assert result["has_custom_rules"] is True


def test_resolve_workspace_failure_falls_back_to_project_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "crane.services.permission_rule_service.resolve_workspace",
        lambda project_dir: (_ for _ in ()).throw(ValueError("not git")),
    )
    service = PermissionRuleService(project_dir=str(tmp_path))
    assert service.project_root == str(tmp_path.resolve())


def test_critique_rules_with_openrouter_api_key_skips_without_key(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("allow", "Read files in the project directory")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = service.critique_rules(model="openrouter/elephant-alpha")
    assert "OPENROUTER_API_KEY" in result["critique"]
    assert result["overall_score"] == 0


def test_critique_rules_calls_openrouter_endpoint(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("allow", "Read files in the project directory")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    payload = {
        "critique": "Rules are clear.",
        "issues_found": [],
        "overall_score": 9,
    }

    class _Response:
        def __init__(self):
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    with monkeypatch.context() as m:
        m.setattr("requests.post", lambda *args, **kwargs: _Response())
        result = service.critique_rules(model="openrouter/elephant-alpha")

    assert result["overall_score"] == 9
    assert result["has_custom_rules"] is True


def test_critique_rules_openrouter_handles_error(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("allow", "Read files in the project directory")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    with monkeypatch.context() as m:
        m.setattr(
            "requests.post",
            lambda *args, **kwargs: (_ for _ in ()).throw(Exception("APIError")),
        )
        result = service.critique_rules(model="openrouter/elephant-alpha")

    assert "LLM critique failed" in result["critique"]
    assert result["overall_score"] == 0


def test_critique_rules_openrouter_empty_response_handles_gracefully(monkeypatch, tmp_path):
    service = _make_service(tmp_path, monkeypatch)
    service.add_rule("allow", "search arxiv")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    class _EmptyResponse:
        def __init__(self):
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": None}}]}

    with monkeypatch.context() as m:
        m.setattr("requests.post", lambda *args, **kwargs: _EmptyResponse())
        result = service.critique_rules(model="openrouter/elephant-alpha")

    assert "rate limit" in result["critique"].lower() or "empty" in result["critique"].lower()
    assert result["overall_score"] == 0
    assert result["has_custom_rules"] is True
