"""投稿前檢查 MCP 工具。

提供 run_submission_check() 口令用於執行完整的投稿前檢查流程。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.submission_pipeline_service import SubmissionPipelineService


def register_tools(mcp):
    """Register submission check tools with the MCP server."""

    @mcp.tool()
    def run_submission_check(
        paper_path: str = "",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        執行完整的投稿前檢查流程。

        整合以下步驟：
        1. 文獻回顧 — 掃瞄現有文獻庫，生成清單
        2. 實驗數據彙總 — 蒐集 repo 中的實驗結果（CSV/JSON/YAML）
        3. FRAMING 分析 — 偵測過度聲張、術語問題等
        4. 論文健康檢查 — Q1 標準評估 + 章節級審查

        動態輸出到 BEFORE_SUBMISSION_RUN{n}/ 目錄。

        Args:
            paper_path: LaTeX 論文主檔案路徑（如 papers/TMLR/TMLR-MAIN.tex）
                若未提供，自動搜尋 papers/ 目錄下的 .tex 檔案
            project_dir: 專案根目錄（預設：當前工作目錄）

        Returns:
            {
                "status": "completed" | "failed",
                "version": 1,
                "submission_dir": "/path/to/BEFORE_SUBMISSION_RUN1/",
                "checkpoints": ["literature_review", "experiment_results", "framing_analysis", "paper_health_check"],
                "reports": {
                    "literature": {"file": "LITERATURE_REVIEW.md", "reference_count": 42, "pdf_complete": 40},
                    "experiments": {"file": "EXP_RESULTS.md", "experiment_count": 156, "data_sources": 5},
                    "framing": {"file": "FRAMING_ANALYSIS.md", "total_issues": 8, "critical": 2, "high": 3},
                    "health": {"file": "PAPER_HEALTH_REPORT.md", "overall_score": 78.5, "readiness": "ready_with_revisions"}
                },
                "completed_at": "2025-03-27T...",
                "error": "..." (if failed)
            }
        """
        if not project_dir:
            project_dir = "."

        root = Path(project_dir)

        # 自動偵測論文路徑
        if not paper_path:
            papers_dir = root / "papers"
            if papers_dir.exists():
                tex_files = list(papers_dir.rglob("*.tex"))
                if tex_files:
                    paper_path = str(tex_files[0])
                else:
                    return {
                        "status": "failed",
                        "error": "No LaTeX file found in papers/ directory",
                    }
            else:
                return {
                    "status": "failed",
                    "error": "No papers/ directory found",
                }

        submission_svc = SubmissionPipelineService(root)

        try:
            result = submission_svc.run_full_check(paper_path)

            return {
                "status": result.status,
                "version": result.version,
                "submission_dir": result.submission_dir,
                "checkpoints": result.checkpoints,
                "reports": result.reports,
                "completed_at": result.completed_at,
                **({"error": result.error} if result.error else {}),
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": f"Submission check failed: {str(e)}",
            }
