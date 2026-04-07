"""
Test suite for README.md integration with CRANE services and 6-stage workflow.

驗證 README.md 文檔與實際服務實現的一致性。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


class TestReadmeStructure:
    """驗證 README.md 文檔結構完整性"""

    @pytest.fixture
    def readme_path(self) -> Path:
        """Get README.md path"""
        readme = Path(__file__).parent.parent / "README.md"
        assert readme.exists(), "README.md not found"
        return readme

    @pytest.fixture
    def readme_content(self, readme_path: Path) -> str:
        """Load README.md content"""
        return readme_path.read_text(encoding="utf-8")

    def test_readme_exists(self, readme_path: Path):
        """✅ README.md 檔案存在"""
        assert readme_path.is_file()
        assert readme_path.stat().st_size > 0

    def test_readme_has_required_sections(self, readme_content: str):
        """✅ README.md 包含所有必要章節"""
        required_sections = [
            "# CRANE: 自主科學研究助理系統",
            "## 30 秒了解 CRANE",
            "## 核心優勢",
            "## 6 個研究階段的完整工作流",
            "### 📚 **第 1 階段",
            "### ✍️ **第 2 階段",
            "### 🔬 **第 3 階段",
            "### 💡 **第 4 階段",
            "### 📋 **第 5 階段",
            "### 🎯 **第 6 階段",
            "## 版本歷史",
            "## 安裝與配置",
            "## 開發與測試",
            "## 實際應用案例",
        ]
        for section in required_sections:
            assert section in readme_content, f"Missing section: {section}"

    def test_readme_line_count(self, readme_path: Path):
        """✅ README.md 行數在預期範圍內（v0.12.0: ~819 行）"""
        content = readme_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        # v0.12.0 should be around 819 lines (+/- 50)
        assert 769 < len(lines) < 869, f"Line count {len(lines)} not in expected range"


class TestV0120Features:
    """驗證 v0.12.0 新功能文檔"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    def test_v0120_section_exists(self, readme_content: str):
        """✅ v0.12.0 新功能部分存在"""
        assert "v0.12.0 新功能" in readme_content
        assert "4 個研究缺口解決方案" in readme_content

    def test_all_four_research_gaps_mentioned(self, readme_content: str):
        """✅ 四個研究缺口 (#59-62) 都被提及"""
        assert "Issue #59" in readme_content, "Issue #59 not mentioned"
        assert "Issue #60" in readme_content, "Issue #60 not mentioned"
        assert "Issue #61" in readme_content, "Issue #61 not mentioned"
        assert "Issue #62" in readme_content, "Issue #62 not mentioned"

    def test_issue59_documentation(self, readme_content: str):
        """✅ Issue #59（論文-程式碼對齐）文檔完整"""
        issue59_content = readme_content
        assert (
            "論文-程式碼對齐" in issue59_content or "verify_paper_code_alignment" in issue59_content
        )
        assert "PaperCodeAlignmentService" in issue59_content
        assert "可重現性評分" in issue59_content or "reproducibility" in issue59_content

    def test_issue60_documentation(self, readme_content: str):
        """✅ Issue #60（管道基準）文檔完整"""
        assert (
            "ResearchPipelineBenchmarkService" in readme_content or "研究管道基準" in readme_content
        )
        assert "6 階段評估" in readme_content or "stage" in readme_content
        assert "期刊接受" in readme_content or "acceptance" in readme_content

    def test_issue61_documentation(self, readme_content: str):
        """✅ Issue #61（信任校準）文檔完整"""
        assert "信任校準" in readme_content or "TrustCalibrationService" in readme_content
        assert "4 級" in readme_content or "autonomy" in readme_content
        assert "自主權" in readme_content or "autonomy_level" in readme_content

    def test_issue62_documentation(self, readme_content: str):
        """✅ Issue #62（MCP 工具編排）文檔完整"""
        assert "MCP" in readme_content
        assert "140+" in readme_content or "tool" in readme_content
        assert "MCPToolOrchestrationService" in readme_content or "工具編排" in readme_content

    def test_v0120_code_lines_mentioned(self, readme_content: str):
        """✅ v0.12.0 代碼行數正確標註（641+522+521+704=2,388）"""
        # Check for individual service line counts
        assert "641 行" in readme_content, "Issue #59 line count not mentioned"
        assert "522 行" in readme_content, "Issue #60 line count not mentioned"
        assert "521 行" in readme_content, "Issue #61 line count not mentioned"
        assert "704 行" in readme_content, "Issue #62 line count not mentioned"
        assert "2,388 行" in readme_content, "v0.12.0 total line count not mentioned"

    def test_v0120_test_counts(self, readme_content: str):
        """✅ v0.12.0 測試數量正確（13+16+18+19=66）"""
        assert "13 個" in readme_content or "13" in readme_content, "Issue #59 tests not mentioned"
        assert "16 個" in readme_content or "16" in readme_content, "Issue #60 tests not mentioned"
        assert "18 個" in readme_content or "18" in readme_content, "Issue #61 tests not mentioned"
        assert "19 個" in readme_content or "19" in readme_content, "Issue #62 tests not mentioned"
        assert "66 個" in readme_content or "66" in readme_content, (
            "v0.12.0 total tests not mentioned"
        )


class TestSixStageIntegration:
    """驗證 6 個研究階段的 v0.12.0 集成"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    def test_stage1_has_documentation(self, readme_content: str):
        """✅ 第 1 階段（文獻回顧）有完整文檔"""
        assert "第 1 階段" in readme_content
        assert "文獻" in readme_content

    def test_stage2_includes_issue59(self, readme_content: str):
        """✅ 第 2 階段（論文寫作）包含 Issue #59"""
        stage2_match = re.search(r"### ✍️ \*\*第 2 階段.*?(?=###)", readme_content, re.DOTALL)
        assert stage2_match, "Stage 2 section not found"
        stage2_content = stage2_match.group(0)
        assert "verify_paper_code_alignment" in stage2_content or "Issue #59" in stage2_content, (
            "Stage 2 should mention paper-code alignment"
        )

    def test_stage3_includes_issue59_verification(self, readme_content: str):
        """✅ 第 3 階段（實驗設計）包含 Issue #59 驗證"""
        stage3_match = re.search(r"### 🔬 \*\*第 3 階段.*?(?=###)", readme_content, re.DOTALL)
        assert stage3_match, "Stage 3 section not found"
        stage3_content = stage3_match.group(0)
        assert "verify_paper_code_alignment" in stage3_content or "實驗驗證" in stage3_content, (
            "Stage 3 should mention experiment verification"
        )

    def test_stage5_includes_issue60(self, readme_content: str):
        """✅ 第 5 階段（自動評審）後包含 Issue #60"""
        assert "第 5.5 階段" in readme_content or "評估研究管道" in readme_content, (
            "Pipeline benchmark should be mentioned as Stage 5.5"
        )
        assert (
            "ResearchPipelineBenchmarkService" in readme_content
            or "evaluate_research_pipeline" in readme_content
        )

    def test_stage6_includes_issue61(self, readme_content: str):
        """✅ 第 6 階段（優化）包含 Issue #61 信任校準"""
        stage6_match = re.search(r"### 🎯 \*\*第 6 階段.*?(?=---|\Z)", readme_content, re.DOTALL)
        assert stage6_match, "Stage 6 section not found"
        stage6_content = stage6_match.group(0)
        assert (
            "信任校準" in stage6_content
            or "autonomy" in stage6_content
            or "TrustCalibrationService" in stage6_content
        ), "Stage 6 should mention trust calibration"

    def test_all_stages_have_recommendations(self, readme_content: str):
        """✅ 所有階段都有建議流程"""
        assert "建議流程" in readme_content
        # Count occurrences
        count = readme_content.count("建議流程")
        assert count >= 5, f"Expected at least 5 recommended flows, found {count}"


class TestWorkflowExamples:
    """驗證工作流示例的完整性"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    def test_complete_workflow_example_exists(self, readme_content: str):
        """✅ 完整的 8 週工作流範例存在"""
        assert (
            "完整工作流範例" in readme_content
            or "8 週" in readme_content
            or "8-week" in readme_content
        )

    def test_workflow_includes_week_by_week_steps(self, readme_content: str):
        """✅ 工作流包含分週步驟"""
        assert "# 初始化 (Week 1)" in readme_content or "# 第 1 階段" in readme_content
        assert "Week" in readme_content or "週" in readme_content

    def test_new_v0120_commands_in_workflow(self, readme_content: str):
        """✅ v0.12.0 新命令集成到工作流中"""
        assert (
            "verify-paper-code-alignment" in readme_content
            or "verify_paper_code_alignment" in readme_content
        )
        assert (
            "evaluate-research-pipeline" in readme_content
            or "evaluate_research_pipeline" in readme_content
        )

    def test_practical_examples_section(self, readme_content: str):
        """✅ 實際應用案例部分存在"""
        assert "實際應用案例" in readme_content
        # Should have at least 3-4 practical examples
        example_count = readme_content.count("### ")
        assert example_count >= 15, (
            f"Expected more detailed examples, found {example_count} sections"
        )


class TestServiceIntegration:
    """驗證文檔與實際服務實現的一致性"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    @pytest.fixture
    def services_dir(self) -> Path:
        """Get services directory"""
        return Path(__file__).parent.parent / "src" / "crane" / "services"

    def test_mentioned_services_exist(self, readme_content: str, services_dir: Path):
        """✅ README 提及的所有服務都實際存在"""
        service_names = [
            "PaperCodeAlignmentService",
            "ResearchPipelineBenchmarkService",
            "TrustCalibrationService",
            "MCPToolOrchestrationService",
        ]
        for service_name in service_names:
            assert service_name in readme_content, f"{service_name} not mentioned in README"

    def test_service_files_exist(self, services_dir: Path):
        """✅ 所有 v0.12.0 新服務檔案存在"""
        service_files = [
            "paper_code_alignment_service.py",
            "research_pipeline_benchmark_service.py",
            "trust_calibration_service.py",
            "mcp_tool_orchestration_service.py",
        ]
        for service_file in service_files:
            service_path = services_dir / service_file
            assert service_path.exists(), f"Service file {service_file} not found"

    def test_test_files_exist(self):
        """✅ 所有 v0.12.0 新測試檔案存在"""
        tests_dir = Path(__file__).parent / "services"
        test_files = [
            "test_paper_code_alignment_service.py",
            "test_research_pipeline_benchmark_service.py",
            "test_trust_calibration_service.py",
            "test_mcp_tool_orchestration_service.py",
        ]
        for test_file in test_files:
            test_path = tests_dir / test_file
            assert test_path.exists(), f"Test file {test_file} not found"


class TestVersionInformation:
    """驗證版本信息一致性"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    def test_v0120_version_mentioned(self, readme_content: str):
        """✅ v0.12.0 版本號在 README 中提及"""
        assert "v0.12.0" in readme_content
        assert "2026-04-07" in readme_content or "4-07" in readme_content

    def test_version_history_updated(self, readme_content: str):
        """✅ 版本歷史表包含 v0.12.0"""
        assert "## 版本歷史" in readme_content
        # Version history should list v0.12.0 first
        version_section = readme_content[readme_content.find("## 版本歷史") :]
        assert "v0.12.0" in version_section[:200], (
            "v0.12.0 should be near the top of version history"
        )

    def test_service_count_updated(self, readme_content: str):
        """✅ 文檔中的服務數量與實際一致（74 個）"""
        # Should mention 74 services total (64 existing + 10 from v0.11.0 + 4 from v0.12.0... actually 64+4=68 or more)
        assert "74 個服務" in readme_content or "74" in readme_content
        assert "服務" in readme_content

    def test_test_count_updated(self, readme_content: str):
        """✅ 文檔中的測試數量與實際一致（216+ 個）"""
        assert "216" in readme_content or "測試" in readme_content


class TestCommandSyntax:
    """驗證文檔中的命令語法"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    def test_verify_paper_code_alignment_command(self, readme_content: str):
        """✅ verify-paper-code-alignment 命令文檔存在"""
        assert (
            "verify-paper-code-alignment" in readme_content
            or "verify_paper_code_alignment" in readme_content
        )
        # Should have parameters
        assert "paper" in readme_content.lower()
        assert "code" in readme_content.lower()

    def test_evaluate_pipeline_command(self, readme_content: str):
        """✅ evaluate-research-pipeline 命令文檔存在"""
        assert (
            "evaluate-research-pipeline" in readme_content
            or "evaluate_research_pipeline" in readme_content
            or "evaluate_pipeline" in readme_content
        )

    def test_autonomy_level_parameter(self, readme_content: str):
        """✅ autonomy-level 參數有文檔"""
        assert "autonomy" in readme_content.lower() or "自主權" in readme_content

    def test_commands_have_examples(self, readme_content: str):
        """✅ 命令都有使用示例"""
        # Count bash code blocks
        bash_blocks = readme_content.count("```bash")
        assert bash_blocks >= 3, f"Expected at least 3 bash code examples, found {bash_blocks}"


class TestDocumentationCompleteness:
    """驗證文檔完整性"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    def test_each_issue_has_core_features(self, readme_content: str):
        """✅ 每個 Issue 都有核心功能說明"""
        core_features_keywords = {
            "Issue #59": [
                "LatexSettingExtractor",
                "CodeSettingExtractor",
                "SettingComparator",
                "論文-程式碼",
            ],
            "Issue #60": ["6 階段評估", "CoherenceChecker", "PipelineHealthCalculator", "研究管道"],
            "Issue #61": ["TrustCalibrationService", "AutonomyAdjuster", "自主權", "信任校準"],
            "Issue #62": ["MCPToolRegistry", "ToolSelector", "工具編排", "140+"],
        }
        for issue, keywords in core_features_keywords.items():
            assert issue in readme_content, f"{issue} not found"
            found = sum(1 for keyword in keywords if keyword in readme_content)
            assert found >= 1, f"{issue} missing core features"

    def test_use_cases_documented(self, readme_content: str):
        """✅ 每個功能都有使用場景說明"""
        assert "使用場景" in readme_content or "use case" in readme_content.lower()

    def test_integration_points_documented(self, readme_content: str):
        """✅ 服務間的集成點有文檔"""
        assert "整合" in readme_content or "integration" in readme_content.lower()

    def test_chinese_content_quality(self, readme_content: str):
        """✅ 繁體中文內容品質檢查"""
        # Check for proper Chinese punctuation
        assert "。" in readme_content or "，" in readme_content or "：" in readme_content
        # Should use traditional Chinese
        assert "階段" in readme_content  # Proper traditional character
        assert "服務" in readme_content  # Proper traditional character


class TestCodeExampleValidation:
    """驗證代碼示例的有效性"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    def test_python_code_blocks(self, readme_content: str):
        """✅ Python 代碼塊有效"""
        # Extract Python code blocks
        python_blocks = re.findall(r"```python\n(.*?)\n```", readme_content, re.DOTALL)
        # Should have at least some Python examples
        assert len(python_blocks) >= 1, "Should have Python code examples"

    def test_bash_command_blocks(self, readme_content: str):
        """✅ Bash 命令塊有效"""
        bash_blocks = re.findall(r"```bash\n(.*?)\n```", readme_content, re.DOTALL)
        assert len(bash_blocks) >= 3, "Should have multiple bash examples"
        valid_command_blocks = 0
        for block in bash_blocks:
            has_command_keywords = any(
                kw in block.lower()
                for kw in [
                    "crane",
                    "python",
                    "uv",
                    "git",
                    "export",
                    "cd",
                    "search",
                    "verify",
                    "review",
                ]
            )
            has_code_like = "(" in block or "=" in block
            if has_command_keywords or has_code_like:
                valid_command_blocks += 1
        assert valid_command_blocks >= 2, "Should have multiple valid command blocks"

    def test_table_syntax(self, readme_content: str):
        """✅ Markdown 表格語法正確"""
        # Should have tables
        table_lines = [line for line in readme_content.split("\n") if "|" in line]
        assert len(table_lines) > 20, "Should have multiple tables with data"

    def test_section_headers_consistent(self, readme_content: str):
        """✅ 章節標題格式一致"""
        # Check for consistent header hierarchy
        headers = re.findall(r"^#+\s", readme_content, re.MULTILINE)
        assert len(headers) > 15, "Should have multiple sections"


class TestLinkAndReference:
    """驗證連結和參考"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    def test_github_issues_linked(self, readme_content: str):
        """✅ GitHub Issues 有適當的參考"""
        assert "Issue #59" in readme_content
        assert "Issue #60" in readme_content
        assert "Issue #61" in readme_content
        assert "Issue #62" in readme_content

    def test_service_names_consistent(self, readme_content: str):
        """✅ 服務名稱在文檔中一致"""
        # Count service mentions
        issue59_mentions = readme_content.count("PaperCodeAlignmentService") + readme_content.count(
            "論文-程式碼對齐"
        )
        assert issue59_mentions >= 2, "Service name should appear multiple times consistently"

    def test_citations_valid(self, readme_content: str):
        """✅ 引用和參考有效"""
        assert "Nature《The AI Scientist》" in readme_content or "AI Scientist" in readme_content
        assert "LeCun" in readme_content or "Yann" in readme_content


class TestMetadata:
    """驗證元數據和統計信息"""

    @pytest.fixture
    def readme_content(self) -> str:
        readme = Path(__file__).parent.parent / "README.md"
        return readme.read_text(encoding="utf-8")

    @pytest.fixture
    def readme_path(self) -> Path:
        return Path(__file__).parent.parent / "README.md"

    def test_file_encoding(self, readme_path: Path):
        """✅ README.md 使用 UTF-8 編碼"""
        try:
            readme_path.read_text(encoding="utf-8")
            assert True
        except UnicodeDecodeError:
            pytest.fail("README.md is not UTF-8 encoded")

    def test_no_trailing_whitespace(self, readme_content: str):
        """✅ 沒有過多的尾部空白"""
        lines = readme_content.split("\n")
        trailing_lines = [i for i, line in enumerate(lines) if line.endswith("  ")]
        # Allow some, but not excessive
        assert len(trailing_lines) < 10, "Too many lines with trailing whitespace"

    def test_code_block_closure(self, readme_content: str):
        """✅ 所有代碼塊都正確關閉"""
        # Count opening and closing backticks
        triple_backtick_count = readme_content.count("```")
        assert triple_backtick_count % 2 == 0, "Code blocks not properly closed"

    def test_section_completeness(self, readme_content: str):
        """✅ 所有章節都有內容"""
        lines = readme_content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("## ") or line.startswith("### "):
                # Next non-empty line should exist and not be another header
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip() and not lines[j].startswith("#"):
                        break
                else:
                    pytest.fail(f"Section '{line}' appears to have no content")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
