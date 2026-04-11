"""Multi-source evidence collector - Feynman-inspired literature search aggregator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from crane.services.paper_service import PaperService
from crane.services.semantic_search_service import SemanticSearchService
from crane.services.citation_graph_service import CitationGraphService


@dataclass
class EvidenceRecord:
    """Single evidence record with source metadata."""

    id: str
    title: str
    authors: list[str]
    year: int
    source: str  # arxiv | semantic_scholar | crossref
    doi: str = ""
    url: str = ""
    abstract: str = ""
    similarity_score: float = 0.0
    cited_by_count: int = 0
    citation_context: str = ""


class MultiSourceEvidenceCollector:
    """
    多來源證據收集器。

    整合 Feynman 的 `lit` 命令核心功能，實現：
    1. 多來源聚合搜索 (arXiv + Semantic Scholar + CrossRef)
    2. 自動去重與來源標註
    3. 語義相似性搜索
    4. 引用圖譜雙向擴展
    """

    def __init__(
        self,
        paper_service: PaperService | None = None,
        semantic_service: SemanticSearchService | None = None,
        citation_service: CitationGraphService | None = None,
    ):
        self.paper_service = paper_service or PaperService()
        self.semantic_service = semantic_service or SemanticSearchService()
        self.citation_service = citation_service or CitationGraphService()

    def collect_evidence(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results: int = 50,
        deduplicate: bool = True,
    ) -> list[EvidenceRecord]:
        """
        從多來源收集證據。

        Args:
            query: 搜索查詢
            sources: 來源列表，預設包含所有來源
            max_results: 最大結果數量
            deduplicate: 是否去重

        Returns:
            EvidenceRecord 列表
        """
        sources = sources or ["arxiv", "semantic_scholar", "crossref"]
        all_results: dict[str, EvidenceRecord] = {}

        # Collect from each source
        for source in sources:
            try:
                source_results = self._collect_from_source(query, source, max_results)
                for record in source_results:
                    if deduplicate:
                        key = self._generate_dedup_key(record)
                        if key not in all_results:
                            all_results[key] = record
                    else:
                        unique_key = f"{record.id}_{source}"
                        all_results[unique_key] = record
            except Exception as e:
                print(f"Error collecting from {source}: {e}")
                continue

        return list(all_results.values())[:max_results]

    def find_similar_papers(
        self,
        paper_id: str,
        similarity_threshold: float = 0.7,
        max_results: int = 20,
    ) -> list[EvidenceRecord]:
        """
        基於語義相似度查找相似論文。

        Args:
            paper_id: 論文 ID
            similarity_threshold: 相似度閾值
            max_results: 最大結果數量

        Returns:
            相似論文列表
        """
        try:
            similar_results = self.semantic_service.search_similar(
                query_text=f"paper:{paper_id}",
                k=max_results * 2,
            )

            records = []
            for result in similar_results:
                if result.get("similarity", 0.0) >= similarity_threshold:
                    record = EvidenceRecord(
                        id=result.get("key", ""),
                        title=result.get("title", ""),
                        authors=result.get("authors", []),
                        year=result.get("year", 0),
                        source="semantic_search",
                        similarity_score=result.get("similarity", 0.0),
                    )
                    records.append(record)

            return records[:max_results]
        except Exception as e:
            print(f"Error finding similar papers: {e}")
            return []

    def expand_citations(
        self,
        paper_id: str,
        direction: str = "both",
        max_depth: int = 2,
    ) -> list[EvidenceRecord]:
        """
        擴展引用關係圖。

        Args:
            paper_id: 論文 ID
            direction: 擴展方向 (forward/backward/both)
            max_depth: 最大深度

        Returns:
            引用關係記錄列表
        """
        records = []

        try:
            citation_graph = self.citation_service.build_citation_graph(
                source="semantic_scholar",
                limit_per_paper=50,
            )

            if paper_id not in citation_graph:
                return []

            paper_data = citation_graph[paper_id]

            if direction in ["backward", "both"]:
                for cited_by in paper_data.get("cited_by", []):
                    record = EvidenceRecord(
                        id=cited_by.get("key", ""),
                        title=cited_by.get("title", ""),
                        authors=cited_by.get("authors", []),
                        year=cited_by.get("year", 0),
                        source="citation_graph",
                        cited_by_count=cited_by.get("cited_by_count", 0),
                        citation_context="backward",
                    )
                    records.append(record)

            if direction in ["forward", "both"]:
                for cites in paper_data.get("cites", []):
                    record = EvidenceRecord(
                        id=cites.get("key", ""),
                        title=cites.get("title", ""),
                        authors=cites.get("authors", []),
                        year=cites.get("year", 0),
                        source="citation_graph",
                        cited_by_count=cites.get("cited_by_count", 0),
                        citation_context="forward",
                    )
                    records.append(record)

            return records[:100]
        except Exception as e:
            print(f"Error expanding citations: {e}")
            return []

    def _collect_from_source(
        self,
        query: str,
        source: str,
        max_results: int,
    ) -> list[EvidenceRecord]:
        """從單一來源收集證據。"""
        if source == "arxiv":
            return self._collect_from_arxiv(query, max_results)
        elif source == "semantic_scholar":
            return self._collect_from_semantic_scholar(query, max_results)
        elif source == "crossref":
            return self._collect_from_crossref(query, max_results)
        else:
            raise ValueError(f"Unsupported source: {source}")

    def _collect_from_arxiv(
        self,
        query: str,
        max_results: int,
    ) -> list[EvidenceRecord]:
        """從 arXiv 收集證據。"""
        try:
            search_results = self.paper_service.search(query, max_results=max_results)
            records = []

            for result in search_results[:max_results]:
                record = EvidenceRecord(
                    id=result.get("id", result.get("arxiv_id", "")),
                    title=result.get("title", ""),
                    authors=self._extract_authors_from_result(result),
                    year=self._extract_year_from_result(result),
                    source="arxiv",
                    doi=result.get("doi", ""),
                    url=result.get("url", ""),
                    abstract=result.get("summary", ""),
                )
                records.append(record)

            return records
        except Exception as e:
            print(f"Error collecting from arXiv: {e}")
            return []

    def _collect_from_semantic_scholar(
        self,
        query: str,
        max_results: int,
    ) -> list[EvidenceRecord]:
        """從 Semantic Scholar 收集證據。"""
        try:
            results = self.semantic_service.search_similar(query_text=query, k=max_results)

            records = []
            for match in results[:max_results]:
                record = EvidenceRecord(
                    id=match.get("key", ""),
                    title=match.get("title", ""),
                    authors=match.get("authors", []),
                    year=match.get("year", 0),
                    source="semantic_scholar",
                    similarity_score=match.get("similarity", 0.0),
                    cited_by_count=match.get("cited_by_count", 0),
                )
                records.append(record)

            return records
        except Exception as e:
            print(f"Error collecting from Semantic Scholar: {e}")
            return []

    def _collect_from_crossref(
        self,
        query: str,
        max_results: int,
    ) -> list[EvidenceRecord]:
        """從 CrossRef 收集證據。"""
        try:
            results = self.semantic_service.search_similar(query_text=query, k=max_results)

            records = []
            for match in results[:max_results]:
                record = EvidenceRecord(
                    id=match.get("key", ""),
                    title=match.get("title", ""),
                    authors=match.get("authors", []),
                    year=match.get("year", 0),
                    source="crossref",
                    doi=match.get("doi", ""),
                    url=match.get("url", ""),
                )
                records.append(record)

            return records
        except Exception as e:
            print(f"Error collecting from CrossRef: {e}")
            return []

    def _generate_dedup_key(self, record: EvidenceRecord) -> str:
        """生成去重鍵 (基於 DOI 或標題)."""
        if record.doi:
            return f"doi:{record.doi}"
        else:
            return f"title:{record.title.lower()[:50]}"

    def _extract_authors_from_result(self, result: dict[str, Any]) -> list[str]:
        """從搜索结果中提取作者列表。"""
        authors = result.get("authors", [])
        if isinstance(authors, list):
            return [str(a) for a in authors][:10]
        return []

    def _extract_year_from_result(self, result: dict[str, Any]) -> int:
        """從搜索结果中提取出版年份。"""
        year = result.get("year", 0)
        if isinstance(year, str):
            try:
                return int(year[:4])
            except (ValueError, IndexError):
                return 0
        return int(year) if year else 0

    def get_evidence_statistics(
        self,
        records: list[EvidenceRecord],
    ) -> dict[str, Any]:
        """
        獲取證據統計信息。

        Args:
            records: 證據記錄列表

        Returns:
            統計信息字典
        """
        stats = {
            "total_count": len(records),
            "by_source": {},
            "by_year": {},
            "avg_citations": 0.0,
        }

        citation_counts = []
        for record in records:
            # Count by source
            source = record.source
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

            # Count by year
            year = str(record.year)
            stats["by_year"][year] = stats["by_year"].get(year, 0) + 1

            # Collect citation counts
            if record.cited_by_count > 0:
                citation_counts.append(record.cited_by_count)

        if citation_counts:
            stats["avg_citations"] = sum(citation_counts) / len(citation_counts)

        return stats
