# CRANE Q2 開發計畫

## 一、現狀盤點

### 已完成 (Q1)

| 項目 | 狀態 | 測試 |
|------|------|------|
| PaperProvider 抽象層 | ✅ | 286 passed |
| ArxivProvider | ✅ | 包含在內 |
| ProviderRegistry | ✅ | 包含在內 |
| Provenance 追蹤系統 | ✅ | 包含在內 |
| Pipeline label 修正 | ✅ | 包含在內 |

### 待開發 (Q2)

| 項目 | 優先級 | 預估工時 |
|------|--------|----------|
| OpenAlex Provider | 🔴 高 | 1-2 週 |
| Semantic Scholar Provider | 🔴 高 | 1-2 週 |
| 元資料標準化與去重 | 🔴 高 | 1-2 週 |
| Crossref Provider | 🟡 中 | 1 週 |
| 篩選與比較工作流 | 🟡 中 | 4-6 週 |
| Pipeline 可靠性強化 | 🔴 高 | 2-4 週 |

---

## 二、架構設計

### 2.1 Provider 架構

```
src/crane/providers/
├── __init__.py
├── base.py              # UnifiedMetadata + PaperProvider ABC
├── arxiv.py             # ArxivProvider (已完成)
├── openalex.py          # OpenAlexProvider (待開發)
├── semantic_scholar.py  # SemanticScholarProvider (待開發)
├── crossref.py          # CrossrefProvider (待開發)
├── registry.py          # ProviderRegistry (已完成)
└── normalization.py     # 元資料正規化 (待開發)
```

### 2.2 Provider 介面

```python
class PaperProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[UnifiedMetadata]: ...
    
    @abstractmethod
    def get_by_id(self, paper_id: str) -> UnifiedMetadata | None: ...
    
    @abstractmethod
    def get_by_doi(self, doi: str) -> UnifiedMetadata | None: ...
```

### 2.3 元資料標準化

```python
@dataclass
class UnifiedMetadata:
    title: str
    authors: list[str]
    year: int
    doi: str
    abstract: str
    source: str              # "arxiv", "openalex", "semantic_scholar"
    source_id: str           # Source-specific ID
    url: str
    pdf_url: str
    citations: int           # Citation count
    references: list[str]   # Cited paper IDs
    provenance: Provenance   # Source tracking
```

---

## 三、實作計畫

### Sprint 1: 多來源檢索 (2 週)

#### Week 1: OpenAlex Provider
- [ ] 實作 OpenAlexProvider
- [ ] 支援關鍵字搜尋
- [ ] 支援 DOI 查詢
- [ ] 支援引用網路查詢
- [ ] 撰寫測試

#### Week 2: Semantic Scholar Provider
- [ ] 實作 SemanticScholarProvider
- [ ] 支援關鍵字搜尋
- [ ] 支援論文推薦
- [ ] 支援引用網路查詢
- [ ] 撰寫測試

### Sprint 2: 元資料標準化 (2 週)

#### Week 3: 正規化層
- [ ] 實作 MetadataNormalizer
- [ ] 支援多來源轉換
- [ ] 支援去重邏輯
- [ ] 支援衝突解決

#### Week 4: 整合與測試
- [ ] 整合至 ProviderRegistry
- [ ] 整合至 PaperService
- [ ] 端對端測試
- [ ] 效能優化

### Sprint 3: 篩選與比較 (4-6 週)

#### Week 5-6: 篩選工作流
- [ ] 實作 screen_references 工具
- [ ] 支援納入/排除決策
- [ ] 支援決策記錄
- [ ] 撰寫測試

#### Week 7-8: 比較工作流
- [ ] 實作 compare_papers 工具
- [ ] 支援多維度比較
- [ ] 支援比較矩陣
- [ ] 撰寫測試

#### Week 9-10: 差距分析
- [ ] 實作 extract_gaps 工具
- [ ] 支援研究缺口識別
- [ ] 支援缺口報告
- [ ] 撰寫測試

---

## 四、API 整合

### 4.1 OpenAlex API

**優勢：**
- 免費開放 API
- 涵蓋 250M+ 學術作品
- 支援 DOI、PMID 等多種 ID
- 提供引用網路資料

**端點：**
- 搜尋：`https://api.openalex.org/works?search=...`
- DOI 查詢：`https://api.openalex.org/works/doi:...`
- 引用網路：`https://api.openalex.org/works/{id}?select=cited_by_count,referenced_works`

### 4.2 Semantic Scholar API

**優勢：**
- 免費 API（需申請 Key）
- 豐富的引用網路資料
- 支援論文推薦
- 提供影響力指標

**端點：**
- 搜尋：`https://api.semanticscholar.org/graph/v1/paper/search`
- DOI 查詢：`https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}`
- 引用網路：`/paper/{id}?fields=citations,references`
- 推薦：`/recommendations/v1/papers/forpaper/{id}`

---

## 五、測試策略

### 5.1 單元測試

每個 Provider 需要：
- `test_search_returns_unified_metadata_list`
- `test_get_by_id_returns_single_result`
- `test_get_by_doi_returns_single_result`
- `test_error_handling`

### 5.2 整合測試

- `test_provider_registry_search_all`
- `test_metadata_normalization`
- `test_deduplication`
- `test_conflict_resolution`

### 5.3 端對端測試

- `test_pipeline_with_multiple_providers`
- `test_screening_workflow`
- `test_comparison_workflow`

---

## 六、里程碑

| 里程碑 | 目標日期 | 產出 |
|--------|----------|------|
| M1: OpenAlex Provider | 2 週後 | 2+ Providers |
| M2: 元資料標準化 | 4 週後 | 去重與衝突解決 |
| M3: 篩選工作流 | 8 週後 | screen_references 工具 |
| M4: 比較工作流 | 10 週後 | compare_papers 工具 |

---

## 七、風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| API 限制 | 無法查詢 | 實作快取與重試機制 |
| 元資料不一致 | 去重困難 | 多策略比對（DOI、標題、作者） |
| 工時延誤 | 功能延遲 | 優先實作核心功能 |

---

## 八、成功指標

- [ ] 支援 4+ 學術資料庫
- [ ] 元資料準確度 > 95%
- [ ] 去重準確度 > 90%
- [ ] 測試覆蓋率 > 80%
- [ ] 端對端 Pipeline 成功率 > 95%
