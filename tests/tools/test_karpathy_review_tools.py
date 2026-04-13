"""Tests for Karpathy Coding Review MCP tools."""

from __future__ import annotations

import pytest

from crane.tools.karpathy_review import register_tools


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


class _ToolCollector:
    """Minimal MCP stub that collects registered tools by name."""

    def __init__(self):
        self.tools: dict = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


# ===========================================================================
# Registration
# ===========================================================================


class TestRegistration:
    def test_all_five_tools_registered(self, tools):
        expected = {
            "plan_experiment_implementation",
            "check_code_simplicity",
            "review_code_changes",
            "define_experiment_success_criteria",
            "karpathy_review",
        }
        assert expected <= set(tools.keys())


# ===========================================================================
# plan_experiment_implementation (Principle 1)
# ===========================================================================


class TestPlanExperimentImplementation:
    def test_returns_required_keys(self, tools):
        result = tools["plan_experiment_implementation"]("Add a caching layer to the service")
        for key in ("task", "assumptions", "interpretations", "simpler_alternatives",
                    "success_criteria", "checkpoints", "clarifying_questions"):
            assert key in result, f"Missing key: {key}"

    def test_task_echoed(self, tools):
        task = "Refactor the training loop"
        result = tools["plan_experiment_implementation"](task)
        assert result["task"] == task

    def test_assumptions_is_list(self, tools):
        result = tools["plan_experiment_implementation"]("Fix a bug in the encoder")
        assert isinstance(result["assumptions"], list)
        assert len(result["assumptions"]) >= 1

    def test_checkpoints_are_ordered(self, tools):
        result = tools["plan_experiment_implementation"]("Add new tool to MCP server")
        checkpoints = result["checkpoints"]
        assert isinstance(checkpoints, list)
        assert len(checkpoints) >= 3

    def test_cache_task_suggests_simplification(self, tools):
        result = tools["plan_experiment_implementation"]("Add a cache to speed things up")
        alternatives = " ".join(result["simpler_alternatives"])
        assert "cach" in alternatives.lower()

    def test_tool_task_adds_server_assumption(self, tools):
        result = tools["plan_experiment_implementation"]("Add new tool to the pipeline")
        assumptions_text = " ".join(result["assumptions"])
        assert "server.py" in assumptions_text or "install.sh" in assumptions_text

    def test_clarifying_questions_is_list(self, tools):
        result = tools["plan_experiment_implementation"]("Build a user interface")
        assert isinstance(result["clarifying_questions"], list)
        assert len(result["clarifying_questions"]) >= 1

    def test_existing_code_summary_reduces_questions(self, tools):
        with_summary = tools["plan_experiment_implementation"](
            "Add validation", existing_code_summary="Already have a validate() function"
        )
        without_summary = tools["plan_experiment_implementation"]("Add validation")
        # With a summary we don't ask the duplication question
        assert len(with_summary["clarifying_questions"]) <= len(without_summary["clarifying_questions"])


# ===========================================================================
# check_code_simplicity (Principle 2)
# ===========================================================================


class TestCheckCodeSimplicity:
    def test_returns_required_keys(self, tools):
        result = tools["check_code_simplicity"]("x = 1")
        for key in ("passed", "score", "violations", "summary", "recommendations"):
            assert key in result

    def test_clean_code_passes(self, tools):
        code = "def add(a, b):\n    return a + b\n"
        result = tools["check_code_simplicity"](code)
        assert result["passed"] is True
        assert result["score"] >= 70

    def test_score_is_int(self, tools):
        result = tools["check_code_simplicity"]("pass")
        assert isinstance(result["score"], int)

    def test_violations_is_list(self, tools):
        result = tools["check_code_simplicity"]("pass")
        assert isinstance(result["violations"], list)

    def test_complex_code_has_violations(self, tools):
        # Deep nesting and try/except abuse
        code = (
            "try:\n"
            "    try:\n"
            "        try:\n"
            "            x = 1\n"
            "        except Exception:\n"
            "            pass\n"
            "    except Exception:\n"
            "        pass\n"
            "except Exception:\n"
            "    pass\n"
        )
        result = tools["check_code_simplicity"](code)
        assert len(result["violations"]) > 0

    def test_violation_has_required_fields(self, tools):
        code = "try:\n    x = 1\nexcept Exception:\n    pass\n"
        result = tools["check_code_simplicity"](code)
        if result["violations"]:
            v = result["violations"][0]
            for field in ("principle", "severity", "message", "suggestion"):
                assert field in v

    def test_recommendations_is_list(self, tools):
        result = tools["check_code_simplicity"]("x = 1")
        assert isinstance(result["recommendations"], list)


# ===========================================================================
# review_code_changes (Principle 3)
# ===========================================================================


class TestReviewCodeChanges:
    ORIGINAL = "def foo():\n    return 1\n"
    MODIFIED_TINY = "def foo():\n    return 2\n"
    MODIFIED_BIG = "\n".join([f"line_{i} = {i}" for i in range(200)])

    def test_returns_required_keys(self, tools):
        result = tools["review_code_changes"](self.ORIGINAL, self.MODIFIED_TINY)
        for key in ("passed", "score", "violations", "summary", "recommendations"):
            assert key in result

    def test_no_change_passes(self, tools):
        result = tools["review_code_changes"](self.ORIGINAL, self.ORIGINAL)
        assert result["passed"] is True
        assert result["score"] == 100

    def test_small_change_passes(self, tools):
        result = tools["review_code_changes"](self.ORIGINAL, self.MODIFIED_TINY, "change return value")
        assert result["passed"] is True

    def test_large_change_may_fail(self, tools):
        result = tools["review_code_changes"](self.ORIGINAL, self.MODIFIED_BIG)
        # 200 lines changed → should flag something
        assert len(result["violations"]) > 0

    def test_summary_contains_line_count(self, tools):
        result = tools["review_code_changes"](self.ORIGINAL, self.MODIFIED_TINY)
        assert "line" in result["summary"].lower() or "change" in result["summary"].lower()

    def test_stated_goal_appears_in_summary(self, tools):
        result = tools["review_code_changes"](
            self.ORIGINAL, self.MODIFIED_TINY, stated_goal="fix return value"
        )
        assert "fix return value" in result["summary"]

    def test_violations_have_required_fields(self, tools):
        result = tools["review_code_changes"](self.ORIGINAL, self.MODIFIED_BIG)
        for v in result["violations"]:
            for field in ("principle", "severity", "message", "suggestion"):
                assert field in v


# ===========================================================================
# define_experiment_success_criteria (Principle 4)
# ===========================================================================


class TestDefineExperimentSuccessCriteria:
    def test_returns_required_keys(self, tools):
        result = tools["define_experiment_success_criteria"]("improve accuracy")
        for key in ("goal", "criteria", "metrics", "anti_goals", "verification_steps"):
            assert key in result

    def test_goal_echoed(self, tools):
        goal = "outperform the baseline on F1 score"
        result = tools["define_experiment_success_criteria"](goal)
        assert result["goal"] == goal

    def test_criteria_is_list(self, tools):
        result = tools["define_experiment_success_criteria"]("train a model")
        assert isinstance(result["criteria"], list)

    def test_experiment_domain_has_anti_goals(self, tools):
        result = tools["define_experiment_success_criteria"](
            "improve accuracy", domain="experiment"
        )
        assert len(result["anti_goals"]) > 0

    def test_paper_domain_verification_mentions_traceability(self, tools):
        result = tools["define_experiment_success_criteria"](
            "finalize paper results", domain="paper"
        )
        steps_text = " ".join(result["verification_steps"])
        assert "traceability" in steps_text.lower() or "verify" in steps_text.lower()

    def test_code_domain_verification_mentions_pytest(self, tools):
        result = tools["define_experiment_success_criteria"](
            "add new feature", domain="code"
        )
        steps_text = " ".join(result["verification_steps"])
        assert "pytest" in steps_text

    def test_accuracy_keyword_adds_criterion(self, tools):
        result = tools["define_experiment_success_criteria"](
            "improve accuracy on validation set"
        )
        criteria_text = " ".join(result["criteria"]).lower()
        assert "accuracy" in criteria_text

    def test_verification_steps_is_list(self, tools):
        result = tools["define_experiment_success_criteria"]("run experiment")
        assert isinstance(result["verification_steps"], list)


# ===========================================================================
# karpathy_review (combined)
# ===========================================================================


class TestKarpathyReview:
    SIMPLE_CODE = "def add(a, b):\n    return a + b\n"

    def test_returns_stated_goal(self, tools):
        result = tools["karpathy_review"](self.SIMPLE_CODE, stated_goal="add two numbers")
        assert result["stated_goal"] == "add two numbers"

    def test_returns_domain(self, tools):
        result = tools["karpathy_review"](self.SIMPLE_CODE, domain="code")
        assert result["domain"] == "code"

    def test_overall_passed_present(self, tools):
        result = tools["karpathy_review"](self.SIMPLE_CODE)
        assert "overall_passed" in result

    def test_overall_score_present(self, tools):
        result = tools["karpathy_review"](self.SIMPLE_CODE)
        assert "overall_score" in result

    def test_simplicity_result_present(self, tools):
        result = tools["karpathy_review"](self.SIMPLE_CODE)
        assert "simplicity" in result

    def test_success_criteria_present(self, tools):
        result = tools["karpathy_review"](self.SIMPLE_CODE, stated_goal="add numbers")
        assert "success_criteria" in result

    def test_surgical_absent_when_no_original(self, tools):
        result = tools["karpathy_review"](self.SIMPLE_CODE)
        # When original_code is empty, surgical check is skipped or null
        assert result.get("surgical") is None or "surgical" not in result

    def test_surgical_present_when_original_provided(self, tools):
        original = "def add(a, b):\n    return a - b\n"
        result = tools["karpathy_review"](
            self.SIMPLE_CODE, original_code=original, stated_goal="fix addition"
        )
        assert "surgical" in result
        assert result["surgical"] is not None

    def test_simple_code_passes_overall(self, tools):
        result = tools["karpathy_review"](self.SIMPLE_CODE, domain="code")
        assert result["overall_passed"] is True

    def test_overall_score_is_int_or_float(self, tools):
        result = tools["karpathy_review"](self.SIMPLE_CODE)
        assert isinstance(result["overall_score"], (int, float))
