"""投稿前檢查流程編排服務。

整合文獻回顧、實驗數據、FRAMING分析、論文健康檢查為一體的端到端工作流程。
支持動態版本管理（BEFORE_SUBMISSION_RUN1、RUN2...）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from crane.services.experiment_collation_service import ExperimentCollationService
from crane.services.q1_evaluation_service import Q1EvaluationService
from crane.services.reference_service import ReferenceService
from crane.services.section_review_service import ReviewType, SectionReviewService


@dataclass
class SubmissionCheckResult:
    """投稿前檢查的結果"""

    status: str
    version: int
    submission_dir: str
    checkpoints: list[str]
    reports: dict[str, Any]
    completed_at: str
    error: str = ""


class SubmissionPipelineService:
    """投稿前檢查流程服務"""

    def __init__(self, project_root: str | Path = "."):
        self.project_root = Path(project_root)
        self.references_dir = self.project_root / "references"

    def detect_submission_run_version(self) -> int:
        """偵測動態的 BEFORE_SUBMISSION_RUN 版本號"""
        existing_runs = list(self.project_root.glob("BEFORE_SUBMISSION_RUN*"))
        versions = []

        for run_dir in existing_runs:
            match = re.match(r"BEFORE_SUBMISSION_RUN(\d+)", run_dir.name)
            if match:
                versions.append(int(match.group(1)))

        return max(versions) + 1 if versions else 1

    def create_submission_workspace(self) -> tuple[Path, int]:
        """建立新的投稿檢查工作區"""
        version = self.detect_submission_run_version()
        submission_dir = self.project_root / f"BEFORE_SUBMISSION_RUN{version}"

        submission_dir.mkdir(parents=True, exist_ok=True)
        (submission_dir / "reports").mkdir(exist_ok=True)
        (submission_dir / "references").mkdir(exist_ok=True)

        return submission_dir, version

    def generate_literature_review(self, submission_dir: Path) -> dict[str, Any]:
        """從現有文獻庫生成文獻回顧報告"""
        ref_svc = ReferenceService(str(self.references_dir))

        # Retrieve full details for each reference
        keys = ref_svc.get_all_keys()
        references: list[dict[str, Any]] = []
        for key in keys:
            try:
                references.append(ref_svc.get(key))
            except ValueError:
                continue

        md = "# 文獻回顧\n\n"
        md += f"**生成時間**：{datetime.now().isoformat()}\n"
        md += f"**總文獻數**：{len(references)}\n\n"

        if not references:
            md += "❌ 未發現任何文獻\n"
            report_path = submission_dir / "reports" / "LITERATURE_REVIEW.md"
            report_path.write_text(md, encoding="utf-8")
            return {"file": str(report_path), "reference_count": 0}

        md += "## PDF 確認清單\n\n"
        md += "| # | 論文 | 作者 | 年份 | PDF 狀態 |\n"
        md += "|---|------|------|------|----------|\n"

        pdf_count = 0
        for idx, ref in enumerate(references, 1):
            pdf_path = self.references_dir / "pdfs" / f"{ref['key']}.pdf"
            pdf_status = "✅ 已下載" if pdf_path.exists() else "❌ 未下載"
            if pdf_path.exists():
                pdf_count += 1

            authors_str = (
                f"{ref['authors'][0]} et al."
                if len(ref.get("authors") or []) > 1
                else ref.get("authors", ["Unknown"])[0]
                if ref.get("authors")
                else "Unknown"
            )
            md += f"| {idx} | {ref['title'][:40]}... | {authors_str} | {ref['year']} | {pdf_status} |\n"

        md += f"\n**PDF 完整度**：{pdf_count}/{len(references)} ({100 * pdf_count // len(references)}%)\n\n"

        annotated_references = []
        for ref in references:
            annotations = ref.get("ai_annotations") or {}
            if annotations.get("summary") or annotations.get("key_contributions"):
                annotated_references.append(ref)

        md += "## AI 註解摘要\n\n"
        if not annotated_references:
            md += "- 無 ai_annotations 摘要可用\n\n"
        else:
            for ref in annotated_references:
                annotations = ref.get("ai_annotations") or {}
                md += f"### {ref['title']}\n"
                if annotations.get("summary"):
                    md += f"- **摘要**：{annotations['summary']}\n"
                contributions = annotations.get("key_contributions") or []
                if contributions:
                    md += f"- **貢獻**：{'; '.join(str(c) for c in contributions)}\n"
                md += "\n"

        md += "## 文獻詳細清單\n\n"
        for ref in references:
            md += f"### {ref['title']}\n"
            md += f"- **作者**：{', '.join(ref.get('authors') or ['Unknown'])}\n"
            md += f"- **年份**：{ref['year']}\n"
            md += f"- **DOI**：{ref.get('doi', '')}\n"
            if ref.get("abstract"):
                md += f"- **摘要**：{ref['abstract'][:200]}...\n"
            md += "\n"

        report_path = submission_dir / "reports" / "LITERATURE_REVIEW.md"
        report_path.write_text(md, encoding="utf-8")

        return {
            "file": str(report_path),
            "reference_count": len(references),
            "pdf_complete": pdf_count,
            "annotated_references": len(annotated_references),
        }

    def generate_experiment_results(self, submission_dir: Path) -> dict[str, Any]:
        """整理實驗數據"""
        exp_svc = ExperimentCollationService(self.project_root)
        collation = exp_svc.collate_all()

        md = exp_svc.to_markdown(collation)

        report_path = submission_dir / "reports" / "EXP_RESULTS.md"
        report_path.write_text(md, encoding="utf-8")

        return {
            "file": str(report_path),
            "experiment_count": collation.total_metrics,
            "data_sources": collation.total_files,
        }

    def generate_framing_analysis(self, paper_path: str, submission_dir: Path) -> dict[str, Any]:
        """生成 FRAMING 分析建議"""
        review_svc = SectionReviewService()

        review = review_svc.review_paper(paper_path, review_types=[ReviewType.FRAMING])

        md = "# Framing 分析與建議\n\n"
        md += f"**分析時間**：{datetime.now().isoformat()}\n"
        md += f"**論文**：{Path(paper_path).name}\n\n"

        total_issues = 0
        critical_count = 0
        high_count = 0

        md += "## 摘要\n\n"
        for section in review.sections:
            for issue in section.issues:
                total_issues += 1
                if issue.severity.value == "critical":
                    critical_count += 1
                elif issue.severity.value == "high":
                    high_count += 1

        md += f"- **嚴重問題**：{critical_count} 個\n"
        md += f"- **高優先級**：{high_count} 個\n"
        md += f"- **總計**：{total_issues} 個問題\n\n"

        md += "## 逐章節分析\n\n"
        for section in review.sections:
            if not section.issues:
                continue

            md += f"### {section.name}\n\n"
            for issue in section.issues:
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(issue.severity.value, "⚪")

                md += f"{severity_emoji} **{issue.issue}**\n"
                md += f"- 嚴重度：{issue.severity.value}\n"
                md += f"- 位置：{issue.location}\n"
                md += f"- 原文：`{issue.original[:80]}...`\n"
                md += f"- 建議：{issue.suggestion}\n\n"

        report_path = submission_dir / "reports" / "FRAMING_ANALYSIS.md"
        report_path.write_text(md, encoding="utf-8")

        return {
            "file": str(report_path),
            "total_issues": total_issues,
            "critical": critical_count,
            "high": high_count,
        }

    def generate_paper_health_check(self, paper_path: str, submission_dir: Path) -> dict[str, Any]:
        """執行完整的論文健康檢查"""
        review_svc = SectionReviewService()
        q1_svc = Q1EvaluationService()

        section_review = review_svc.review_paper(paper_path)
        q1_eval = q1_svc.evaluate(paper_path)

        md = "# 投稿前健康檢查報告\n\n"
        md += f"**檢查時間**：{datetime.now().isoformat()}\n"
        md += f"**論文**：{Path(paper_path).name}\n\n"

        md += "## 執行摘要\n\n"
        md += f"- **Q1 評估得分**：{q1_eval.overall_score:.2f}/100\n"
        md += f"- **準備度**：{q1_eval.readiness}\n"
        md += f"- **章節審查**：{len(section_review.sections)} 章節\n\n"

        md += "## Q1 期刊標準評估\n\n"
        md += f"### 總體評分：{q1_eval.overall_score:.2f}/100\n"
        md += f"### 準備度：{q1_eval.readiness}\n\n"

        md += "### 各項評估\n\n"
        for criterion in q1_eval.criteria:
            md += f"#### {criterion.name}\n"
            md += f"- **評分**：{criterion.score.value}\n"
            md += f"- **權重**：{criterion.weight}\n"
            if criterion.evidence:
                md += f"- **證據**：{', '.join(criterion.evidence[:3])}\n"
            if criterion.suggestions:
                md += f"- **建議**：{', '.join(criterion.suggestions[:2])}\n"
            md += "\n"

        md += "## 章節級審查\n\n"
        for section in section_review.sections:
            md += f"### {section.name}\n"
            md += f"- **得分**：{section.score:.2f}\n"

            if section.issues:
                md += f"- **問題數**：{len(section.issues)}\n"
                issue_types = {}
                for issue in section.issues:
                    issue_type = issue.type.value
                    issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
                md += f"- **問題類型**：{', '.join(f'{k}({v})' for k, v in issue_types.items())}\n"
            else:
                md += "- **問題數**：0 ✅\n"

            md += "\n"

        report_path = submission_dir / "reports" / "PAPER_HEALTH_REPORT.md"
        report_path.write_text(md, encoding="utf-8")

        return {
            "file": str(report_path),
            "overall_score": q1_eval.overall_score,
            "readiness": q1_eval.readiness,
            "section_count": len(section_review.sections),
            "total_issues": sum(len(s.issues) for s in section_review.sections),
        }

    def run_full_check(self, paper_path: str) -> SubmissionCheckResult:
        """執行完整的投稿前檢查"""
        submission_dir, version = self.create_submission_workspace()
        checkpoints = []
        reports = {}

        try:
            checkpoints.append("literature_review")
            reports["literature"] = self.generate_literature_review(submission_dir)

            checkpoints.append("experiment_results")
            reports["experiments"] = self.generate_experiment_results(submission_dir)

            checkpoints.append("framing_analysis")
            reports["framing"] = self.generate_framing_analysis(paper_path, submission_dir)

            checkpoints.append("paper_health_check")
            reports["health"] = self.generate_paper_health_check(paper_path, submission_dir)

            return SubmissionCheckResult(
                status="completed",
                version=version,
                submission_dir=str(submission_dir),
                checkpoints=checkpoints,
                reports=reports,
                completed_at=datetime.now().isoformat(),
            )

        except Exception as e:
            return SubmissionCheckResult(
                status="failed",
                version=version,
                submission_dir=str(submission_dir),
                checkpoints=checkpoints,
                reports=reports,
                completed_at=datetime.now().isoformat(),
                error=str(e),
            )
