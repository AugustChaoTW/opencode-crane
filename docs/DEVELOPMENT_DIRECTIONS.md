# CRANE 開發方向與改進建議

## 一、現狀評估

### 已完成功能 (Q1-Q2)

| 模組 | 功能 | 狀態 | 測試 |
|------|------|------|------|
| **Providers** | arXiv, OpenAlex, Semantic Scholar | ✅ | 302 passed |
| **Services** | Paper, Reference, Task, Citation, Provenance, Metadata, Screening | ✅ | 包含 |
| **Tools** | 26 個 MCP Tools | ✅ | 包含 |
| **Pipeline** | literature-review, full-setup | ✅ | 包含 |
| **可靠性** | Retry 邏輯 | ✅ | 包含 |

### Pipeline 執行流程

```
search → add → download → read → annotate → create_task
   ↓       ↓        ↓         ↓        ↓          ↓
 arXiv   YAML    PDF      TXT    AI摘要    GitHub Issue
```

---

## 二、改進方向分析

### 2.1 短期改進 (1-2 週)

#### A. Pipeline label 修正
**問題**: `create_task` 步驟使用不存在的 labels (`crane`, `kind:task`)
**影響**: Pipeline 在最後一步失敗
**解決**: 已修正 `_build_labels()` 方法，需重新啟動 MCP

#### B. 多來源搜尋整合
**問題**: Pipeline 只使用 arXiv 一個來源
**改進**: 
- 整合 OpenAlex 和 Semantic Scholar
- 自動去重與合併
- 提供更全面的搜尋結果

**實作**:
```python
# 在 pipeline 中支援多來源
def search_step(query: str, sources: list[str] = ["arxiv", "openalex"]):
    results = []
    for source in sources:
        provider = registry.get(source)
        results.extend(provider.search(query))
    return normalizer.normalize(results)
```

#### C. 錯誤處理強化
**問題**: 單一論文下載失敗會中斷整個 pipeline
**改進**: 
- 部分成功模式：跳過失敗項目繼續
- 錯誤報告：記錄失敗原因
- 重試機制：自動重試網路錯誤

### 2.2 中期改進 (1-2 月)

#### D. 論文推薦系統
**功能**: 基於已讀論文推薦相關文獻
**實現**: 
- 使用 Semantic Scholar recommendations API
- 分析引用網路
- 識別相關研究方向

#### E. 自動摘要與比較
**功能**: AI 自動生成論文摘要和比較分析
**實現**:
- 整合 LLM 進行摘要生成
- 多維度比較矩陣自動填充
- 研究缺口自動識別

#### F. 寫作輔助工具
**功能**: 輔助學術論文寫作
**實現**:
- 文獻引用自動格式化
- Related Work 自動生成
- 引用一致性檢查

### 2.3 長期改進 (3-6 月)

#### G. 實驗追蹤系統
**功能**: 追蹤實驗設計、執行、結果
**實現**:
- 實驗記錄 YAML 格式
- 結果比較與分析
- 可重現性驗證

#### H. 團隊協作功能
**功能**: 支援多人研究團隊
**實現**:
- 文獻共享與同步
- 任務分配與追蹤
- 進度同步

#### I. 視覺化儀表板
**功能**: 研究進度視覺化
**實現**:
- 引用網路圖
- 研究時間線
- 進度報表

---

## 三、替代方案評估

### 3.1 現有功能替代方案

| 現有功能 | 替代方案 | 優勢 | 劣勢 |
|----------|----------|------|------|
| **arXiv API** | OpenAlex / Semantic Scholar | 更多元資料 | 需要 API Key |
| **PyPDF2** | pypdf / PyMuPDF | 更穩定、更快 | 需要遷移 |
| **GitHub Issues** | Linear / Notion API | 更豐富功能 | 增加複雜度 |
| **YAML 儲存** | SQLite / PostgreSQL | 更好的查詢效能 | 增加依賴 |
| **檔案式去重** | 向量相似度 | 更準確 | 需要 embedding |

### 3.2 架構替代方案

| 現有架構 | 替代方案 | 適用場景 |
|----------|----------|----------|
| **同步 Pipeline** | 非同步 / 並行處理 | 大量論文處理 |
| **單一 MCP Server** | 微服務架構 | 高併發需求 |
| **本地儲存** | 雲端儲存 (S3) | 團隊協作 |
| **CLI 介面** | Web UI | 非技術使用者 |

---

## 四、優先改進清單

### P0: 立即修正
- [x] Pipeline label 問題 (已修正)
- [ ] 重新啟動 MCP 伺服器

### P1: 本週完成
- [ ] 多來源搜尋整合
- [ ] 錯誤處理強化
- [ ] 部分成功模式

### P2: 本月完成
- [ ] 論文推薦系統
- [ ] 自動摘要生成
- [ ] 比較矩陣自動填充

### P3: 季度目標
- [ ] 寫作輔助工具
- [ ] 實驗追蹤系統
- [ ] 視覺化儀表板

---

## 五、技術債清理

### 需要更新的依賴
- PyPDF2 → pypdf (已棄用)
- feedparser → 最新版本
- requests → httpx (非同步支援)

### 程式碼改進
- 移除重複的 docstrings
- 統一錯誤處理模式
- 增加型別標註覆蓋率

### 測試改進
- 增加整合測試
- 增加效能測試
- 增加邊界情況測試

---

## 六、成功指標

### 短期 (1 個月)
- [ ] Pipeline 成功率 > 95%
- [ ] 支援 3+ 資料來源
- [ ] 錯誤處理覆蓋率 > 80%

### 中期 (3 個月)
- [ ] 論文推薦準確率 > 70%
- [ ] 自動摘要品質評分 > 4/5
- [ ] 使用者滿意度 > 4/5

### 長期 (6 個月)
- [ ] 支援 10+ 研究團隊
- [ ] 處理 1000+ 論文
- [ ] 研究效率提升 > 50%
