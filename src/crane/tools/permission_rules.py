from __future__ import annotations

from typing import Any

from crane.services.permission_rule_service import PermissionRuleService


def register_tools(mcp):
    def _service(project_dir: str | None) -> PermissionRuleService:
        return PermissionRuleService(project_dir=project_dir)

    @mcp.tool()
    def add_permission_rule(
        category: str,
        rule: str,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        return _service(project_dir).add_rule(category=category, rule=rule)

    @mcp.tool()
    def remove_permission_rule(
        category: str,
        rule: str,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        return _service(project_dir).remove_rule(category=category, rule=rule)

    @mcp.tool()
    def list_permission_rules(project_dir: str | None = None) -> dict[str, Any]:
        return _service(project_dir).list_rules()

    @mcp.tool()
    def evaluate_permission_action(
        action: str,
        context: dict[str, Any] | None = None,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        decision = _service(project_dir).evaluate_action(action=action, context=context)
        return {
            "action": action,
            "decision": decision,
        }

    @mcp.tool()
    def show_effective_rules(
        dry_run: bool = False,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        return _service(project_dir).show_effective_rules(dry_run=dry_run)

    @mcp.tool()
    def critique_permission_rules(
        model: str = "gpt-4o-mini",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        return _service(project_dir).critique_rules(model=model)
