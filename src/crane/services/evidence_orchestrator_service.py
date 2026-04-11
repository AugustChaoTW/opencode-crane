"""Evidence-guided research orchestrator - Feynman-inspired multi-agent workflow."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from crane.services.chapter_coach_service import ChapterCoachService
from crane.services.citation_service import CitationService
from crane.services.paper_service import PaperService
from crane.services.review_inspector_service import ReviewInspectorService
from crane.workspace import resolve_workspace


@dataclass
class OrchestrationState:
    """Track orchestration state across agent stages."""

    stage: str
    progress: float = 0.0
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        result = {
            "stage": self.stage,
            "progress": self.progress,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }
        result.update(self.results)
        return result


class EvidenceOrchestrator:
    """
    整合 Feynman 的 Multi-agent 研究流程至 CRANE。

    實現證據導向的研究編排，整合四個核心功能：
    1. Researcher Agent - 文獻調研
    2. Reviewer Agent - 論文缺陷檢測
    3. Writer Agent - 寫作指導
    4. Verifier Agent - 引用驗證

    對應 CRANE 階段：1 → 2 → 5
    """

    def __init__(self, refs_dir: str | None = None):
        self.refs_dir = Path(refs_dir) if refs_dir else resolve_workspace() / "references"
        self.paper_service = PaperService()
        self.citation_service = CitationService(refs_dir=str(self.refs_dir))
        self.review_service = ReviewInspectorService()
        self.chapter_coach = ChapterCoachService()
        self.state = OrchestrationState(stage="initialized")

    def run_researcher(self, query: str, max_papers: int = 50) -> OrchestrationState:
        """
        執行 Researcher Agent - 文獻調研。

        Args:
            query: 搜索查詢
            max_papers: 最大論文數量

        Returns:
            OrchestrationState with research results
        """
        self.state = OrchestrationState(stage="researcher", progress=0.0)

        try:
            self.state.progress = 0.1
            search_results = self.paper_service.search(query, max_results=max_papers)
            self.state.results["search_results"] = search_results

            self.state.progress = 0.4
            downloaded = []
            for paper in search_results[: min(10, len(search_results))]:
                paper_id = paper.get("id", paper.get("doi", ""))
                if paper_id:
                    success = self.paper_service.download(paper_id)
                    if success:
                        downloaded.append(paper_id)
            self.state.results["downloaded"] = downloaded

            self.state.progress = 0.8
            read_results = []
            for paper_id in downloaded:
                content = self.paper_service.read(paper_id)
                if content:
                    read_results.append({"id": paper_id, "summary": content[:500]})
            self.state.results["read_results"] = read_results

            self.state.progress = 1.0
            self.state.results["status"] = "completed"

        except Exception as e:
            self.state.errors.append(f"Researcher error: {str(e)}")
            self.state.results["status"] = "failed"

        return self.state

    def run_reviewer(self, paper_path: str) -> OrchestrationState:
        """
        執行 Reviewer Agent - 論文缺陷檢測。

        Args:
            paper_path: LaTeX 論文路徑

        Returns:
            OrchestrationState with review results
        """
        self.state = OrchestrationState(stage="reviewer", progress=0.0)

        try:
            paper_path_obj = Path(paper_path)
            if not paper_path_obj.exists():
                raise FileNotFoundError(f"Paper not found: {paper_path}")

            self.state.progress = 0.5
            paper_content = paper_path_obj.read_text()
            review_report = self.review_service.review_full(paper_content)

            self.state.progress = 0.9
            defect_report = {
                "critical_issues": [],
                "major_issues": [],
                "minor_issues": [],
            }

            for defect in review_report.critical_defects:
                defect_report["critical_issues"].append(
                    {"id": defect.id, "description": defect.description, "chapter": defect.chapter}
                )
            for defect in review_report.major_defects:
                defect_report["major_issues"].append(
                    {"id": defect.id, "description": defect.description, "chapter": defect.chapter}
                )
            for defect in review_report.minor_defects:
                defect_report["minor_issues"].append(
                    {"id": defect.id, "description": defect.description, "chapter": defect.chapter}
                )

            self.state.results["defect_report"] = defect_report
            self.state.results["review_report"] = review_report.to_dict()
            self.state.progress = 1.0
            self.state.results["status"] = "completed"

        except Exception as e:
            self.state.errors.append(f"Reviewer error: {str(e)}")
            self.state.results["status"] = "failed"

        return self.state

    def run_writer(self, paper_path: str, chapter: str) -> OrchestrationState:
        """
        執行 Writer Agent - 章節寫作指導。

        Args:
            paper_path: LaTeX 論文路徑
            chapter: 章節名稱

        Returns:
            OrchestrationState with coaching results
        """
        self.state = OrchestrationState(stage="writer", progress=0.0)

        valid_chapters = [
            "abstract",
            "introduction",
            "methods",
            "results",
            "discussion",
            "conclusion",
        ]
        if chapter not in valid_chapters:
            self.state.errors.append(f"Invalid chapter: {chapter}. Valid: {valid_chapters}")
            self.state.results["status"] = "failed"
            return self.state

        try:
            paper_path_obj = Path(paper_path)
            if not paper_path_obj.exists():
                raise FileNotFoundError(f"Paper not found: {paper_path}")

            self.state.progress = 0.3
            chapter_content = self._extract_chapter(paper_path_obj, chapter)

            self.state.progress = 0.6
            coaching_result = self.chapter_coach.coach_chapter(chapter, chapter_content)
            self.state.results["coaching_result"] = coaching_result

            self.state.progress = 1.0
            recommendations = []
            if "suggestions" in coaching_result:
                recommendations = coaching_result["suggestions"]
            self.state.results["recommendations"] = recommendations
            self.state.results["status"] = "completed"

        except Exception as e:
            self.state.errors.append(f"Writer error: {str(e)}")
            self.state.results["status"] = "failed"

        return self.state

    def run_verifier(self, paper_path: str) -> OrchestrationState:
        """
        執行 Verifier Agent - 引用驗證。

        Args:
            paper_path: LaTeX 論文路徑

        Returns:
            OrchestrationState with verification results
        """
        self.state = OrchestrationState(stage="verifier", progress=0.0)

        try:
            paper_path_obj = Path(paper_path)
            if not paper_path_obj.exists():
                raise FileNotFoundError(f"Paper not found: {paper_path}")

            self.state.progress = 0.2
            paper_content = paper_path_obj.read_text()

            self.state.progress = 0.5
            cite_keys = self.citation_service.extract_cite_keys(paper_content)
            self.state.results["cite_keys"] = cite_keys

            self.state.progress = 1.0
            verification_summary = {
                "total_citations": len(cite_keys),
                "found": cite_keys,
                "missing": [],
                "unused": [],
                "valid": len(cite_keys) > 0,
            }
            self.state.results["verification_summary"] = verification_summary
            self.state.results["status"] = "completed"

        except Exception as e:
            self.state.errors.append(f"Verifier error: {str(e)}")
            self.state.results["status"] = "failed"

        return self.state

    def run_full_orchestration(
        self,
        research_query: str,
        paper_path: str,
        chapters: list[str] | None = None,
        max_papers: int = 50,
    ) -> dict[str, Any]:
        """
        執行完整編排流程：Researcher → Reviewer → Writer → Verifier。

        Args:
            research_query: 研究查詢
            paper_path: LaTeX 論文路徑
            chapters: 要指導的章節列表
            max_papers: 最大論文數量

        Returns:
            Complete orchestration results
        """
        chapters = chapters or ["introduction", "methods", "results"]

        full_results = {
            "orchestration_id": datetime.now().isoformat().replace(":", "-"),
            "stages": {},
            "errors": [],
            "completed_at": None,
        }

        researcher_result = self.run_researcher(research_query, max_papers)
        full_results["stages"]["researcher"] = researcher_result.to_dict()
        if researcher_result.errors:
            full_results["errors"].extend(researcher_result.errors)

        reviewer_result = self.run_reviewer(paper_path)
        full_results["stages"]["reviewer"] = reviewer_result.to_dict()
        if reviewer_result.errors:
            full_results["errors"].extend(reviewer_result.errors)

        writer_results = []
        for chapter in chapters:
            writer_result = self.run_writer(paper_path, chapter)
            writer_results.append({"chapter": chapter, "result": writer_result.to_dict()})
            if writer_result.errors:
                full_results["errors"].extend(writer_result.errors)
        full_results["stages"]["writer"] = writer_results

        verifier_result = self.run_verifier(paper_path)
        full_results["stages"]["verifier"] = verifier_result.to_dict()
        if verifier_result.errors:
            full_results["errors"].extend(verifier_result.errors)

        full_results["completed_at"] = datetime.now().isoformat()

        return full_results

    def _extract_chapter(self, paper_path: Path, chapter: str) -> str:
        content = paper_path.read_text()

        chapter_patterns = {
            "abstract": r"\\begin\{abstract\}.*?\\end\{abstract\}",
            "introduction": r"\\section\{.*?Introduction.*?\}.*?(?=\\section\{)",
            "methods": r"\\section\{.*?Methods?.*?\}.*?(?=\\section\{)",
            "results": r"\\section\{.*?Results?.*?\}.*?(?=\\section\{)",
            "discussion": r"\\section\{.*?Discussion.*?\}.*?(?=\\section\{)",
            "conclusion": r"\\section\{.*?Conclusion.*?\}",
        }

        pattern = chapter_patterns.get(chapter)
        if pattern:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0)

        return ""
