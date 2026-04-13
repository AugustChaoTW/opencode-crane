# CRANE: 自主科學研究助理系統

**AI 驅動的完整研究自動化系統——從文獻搜索到論文發表的 6 個研究階段。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Server-orange.svg)](https://modelcontextprotocol.io/)

CRANE 提供 **121 個 MCP 工具**，涵蓋完整研究生命週期，對標 Nature 論文《The AI Scientist》的 6 個核心研究階段。CRANE provides **121 MCP Tools** across the full research lifecycle.

---

## 30 秒了解 CRANE

CRANE 是為 [OpenCode](https://github.com/anomalyco/opencode) 構建的**自主科學研究 MCP 伺服器**，實現 Nature 《The AI Scientist》論文提出的完整自動化研究流程。它不僅是一個「論文摘要器」，而是**端到端的科學研究自動化系統**：

- **第 1 階段**：文獻搜索與回顧（多源資料庫、引用圖分析）
- **第 2 階段**：論文寫作與架構規劃（證據優先評估、層級分析）
- **第 3 階段**：實驗設計與執行（超參數優化、樹搜索、消融實驗）
- **第 4 階段**：想法生成與多元性探索（Map Elites、Pareto 前沿）
- **第 5 階段**：自動評審與驗證（5 評審員集合、元評審、校準）
- **第 6 階段**：期刊匹配、因果推理、多輪優化（動態排名、因果圖、迴圈協調）
- **🆕 第 7 階段**：論文可追溯性系統（RQ→貢獻→實驗→圖表→引用→變更影響）

CRANE 確保您的研究結構清晰、可驗證、發表就緒。

---

## 核心優勢

### 🔬 完整的 Nature AI Scientist 實現

CRANE 完整實現了 Nature 論文《The AI Scientist: Towards Fully Autonomous Research in Materials Discovery》提出的 6 個研究階段：

| 階段 | 核心功能 | 服務 |
|------|---------|------|
| **第 1 階段** | 文獻搜索、引用圖、PICOS 篩選 | 多源資料庫適配器 |
| **第 2 階段** | 論文評估（7 維度）、層級分析、位置校準 | EvidenceEvaluationService |
| **第 3 階段** | 實驗生成、代碼合成、超參數優化 | ExperimentGenerationService (570 行) |
| **第 4 階段** | 想法生成、多元性探索、Pareto 優化 | IdeationService (385 行) |
| **第 5 階段** | 自動評審、5 評審員集合、校準 | AutomatedReviewerV2 |
| **第 6 階段** | 期刊匹配、因果推理、多輪優化 | DynamicJournalMatchingService + CausalReasoningEngine |
| **🆕 第 7 階段** | 論文可追溯性、變更影響分析 | TraceabilityService + ImpactGraphService |

### 🗂️ v0.13.0 新功能：論文可追溯性系統（Paper Traceability System）

**核心問題**：論文寫作過程中，研究問題、貢獻聲明、實驗數據、圖表數字彼此分散——數字改了圖沒更新、聲明不一致、reviewer 問題無法快速回應。

**解決方案**：10 個 YAML 文件構成完整研究控制鏈，並自動從 .tex/.pdf 推斷結構：

```
RQ → 貢獻 → 實驗 → 圖表/表格 → 引用 → 變更影響 → 風險 → 資料集 → 產物
```

**自然語言觸發**（直接在 OpenCode 中輸入）：

```
trace this paper
do paper trace
整理這篇研究
```

**10 個追溯文件**（自動存入 `_paper_trace/v{n}/`）：

| 文件 | 內容 |
|------|------|
| `1_contribution.yaml` | 貢獻聲明 + 最強可辯護措辭 + 防過度聲明 |
| `2_experiment.yaml` | 實驗設置 + 正規化數字（鎖定） |
| `3_section_outline.yaml` | 各章節必寫/禁寫事項 + 引用需求 |
| `4_citation_map.yaml` | 引用放置規則（必出現/禁出現 的章節） |
| `5_figure_table_map.yaml` | 圖表精確數字 + 可視化規格 + 更新觸發條件 |
| `6_research_question.yaml` | 研究問題上游錨點（全鏈起點） |
| `7_change_log_impact.yaml` | 變更記錄 + 下游必更新項目（CH001…） |
| `8_limitation_reviewer_risk.yaml` | 評審風險 + 回應策略 + fallback 聲明 |
| `9_dataset_baseline_protocol.yaml` | 資料集 + baseline 協議 + 可重現規則 |
| `10_artifact_index.yaml` | 所有追蹤文件（腳本、檢查點、圖表） |

**版次管理**：每次 trace 產生新版次 `v1/`、`v2/`…，`_paper_trace/README.md` 自動記錄版次歷史。

**跳過廢棄論文**：目錄名稱含 `reject`、`nogo`、`no-go`、`withdrawn`、`abandon`、`cancel` 等字眼的論文自動跳過。

```
00_Paper/
  JLE/          ← 活躍論文 ✓ (掃描)
  TNNLS-nogo/   ← 廢棄論文 ✗ (跳過)
  ESWA/         ← 活躍論文 ✓ (掃描)
```

### 📊 證據優先的 Q1 評估

- **7 維度混合評分**：寫作(12%) + 方法論(18%) + 新穎性(18%) + 評估(20%) + 呈現(8%) + 局限(10%) + 可重現(14%)
- **閾值機制**：方法論/新穎性/評估任一 < 60 則阻止 Q1 認證
- **自動分類**：實驗/系統/理論/綜述檔案

### 🎯 動態期刊匹配與趨勢監控

- **55 本 Q1 期刊**：即時影響因子、接受率、排名變化
- **5 維度加權評分**：範圍(35%) + 貢獻風格(20%) + 評估風格(20%) + 引用(15%) + 運營(10%)
- **趨勢追蹤**：期刊指標歷史分析、異常預警、個性化推薦

### 🧠 因果推理框架

統一整合 8 個 LeCun 因果推理框架：

1. 世界模型推理（因果圖、反事實）
2. 研究層級分析（5 層次定位）
3. 策略決策（Pareto 優化）
4. 第一性原則解構（假設質疑）
5. 實驗設計因果性（干預、內部效度）
6. 期刊決策預測（評審模擬）
7. 論文修改優先化（ROI 估算）
8. 多輪優化協調（收斂檢測）

### 🔄 多輪互動式優化

- **自動循環**：evaluate → plan → rewrite → learn → evaluate
- **收斂檢測**：評分增益 < 1% 時自動終止
- **多會話管理**：同一論文的並行改寫會話
- **進度追蹤**：跨輪次評分趨勢與偏好演化

---

## 6 個研究階段的完整工作流

### 📚 **第 1 階段：文獻回顧與任務規劃**

**目標**：系統搜索、組織、評估相關文獻

| 功能 | 工具 | 說明 |
|------|------|------|
| **初始化專案** | `init_research` | 設置 GitHub 里程碑、標籤、資料夾 |
| **多源搜索** | `search_papers` | arXiv、OpenAlex、alphaXiv 同時搜索 |
| **添加文獻** | `add_reference` | 自動生成 BibTeX、YAML 元數據 |
| **讀取論文** | `read_paper` | 自動下載 PDF、提取全文 |
| **系統篩選** | `screen_papers_by_picos` | PICOS 框架自動篩選 |
| **語義搜索** | `semantic_search` | 向量相似度搜索 |
| **引用圖分析** | `build_citation_graph` | 論文間引用關係、網絡可視化 |
| **識別空白** | `find_citation_gaps` | 檢測遺漏的重要論文 |
| **任務管理** | `create_task` | GitHub Issues 進度追蹤 |

**建議流程**：
```bash
1. init_research(field="AI/ML", type="literature-review")
2. search_papers(query="...", sources=["arxiv", "openalex"])
3. screen_papers_by_picos(...)
4. add_reference(paper_key="vaswani2017", ...)
5. build_citation_graph(seed_papers=["vaswani2017"])
```

### ✍️ **第 2 階段：論文寫作與架構規劃**

**目標**：構建論文結構，整合文獻，評估寫作品質

| 功能 | 工具 | 說明 |
|------|------|------|
| **評估論文** | `evaluate_paper_v2` | 7 維度混合評分 |
| **期刊匹配** | `match_journal_v2` | Q1 期刊推薦 + APC 評估 |
| **段落評審** | `review_paper_sections` | 邏輯、數據、框架問題檢測 |
| **Feynman 問答** | `generate_feynman_session` | 產生刁鑽問題迫使思考 |
| **引用核查** | `check_citation_coverage` | 每段引用完整性 |
| **🆕 追溯分析** | `trace_paper` | 建立 RQ→貢獻→實驗完整鏈 |

### 🔬 **第 3 階段：實驗設計與自動執行**

**目標**：自動化實驗設計、代碼生成、超參數優化

| 功能 | 工具 | 說明 |
|------|------|------|
| **實驗生成** | `generate_experiments` | 從論文方法提取實驗框架 |
| **代碼合成** | `generate_experiment_code` | PyTorch/TensorFlow 代碼生成 |
| **超參優化** | `optimize_hyperparameters` | 貝葉斯/網格/隨機搜索 |
| **消融設計** | `design_ablation_study` | 自動生成消融實驗方案 |
| **🆕 實驗追溯** | `add_experiment` | 記錄實驗到追溯鏈 + 鎖定正規化數字 |

### 💡 **第 4 階段：想法生成與多元性探索**

**目標**：突破研究盲點，探索創新方向

| 功能 | 工具 | 說明 |
|------|------|------|
| **想法生成** | `generate_research_ideas` | 基於知識圖的創意生成 |
| **Pareto 前沿** | `explore_pareto_frontier` | 多目標優化探索 |
| **Map Elites** | `run_map_elites` | 行為空間多樣性探索 |
| **第一性原則** | `apply_first_principles` | 分解研究假設 |

### 📋 **第 5 階段：自動評審與驗證**

**目標**：模擬 5 個評審員，識別論文弱點

| 功能 | 工具 | 說明 |
|------|------|------|
| **集合評審** | `run_automated_review` | 5 評審員 + 元評審 |
| **Feynman 探問** | `generate_feynman_session` | 薄弱點識別 + 問題生成 |
| **修改報告** | `generate_revision_report` | 3 層修改計畫 |
| **🆕 風險追溯** | `add_reviewer_risk` | 評審風險記錄 + 回應策略 |

### 🎯 **第 6 階段：期刊匹配、因果推理、多輪優化**

| 功能 | 工具 | 說明 |
|------|------|------|
| **動態期刊匹配** | `match_journal_v2` | Target/Backup/Safe 三級推薦 |
| **APC 分析** | `analyze_apc` | 費用評估 + 預算適配 |
| **因果推理** | `apply_causal_reasoning` | 8 LeCun 框架統一 API |
| **多輪優化** | `run_iterative_optimization` | 自動收斂協調 |
| **投稿模擬** | `simulate_submission_outcome` | 接受概率預測 |

---

## 🆕 第 7 階段：論文可追溯性系統（v0.13.0）

**核心理念**：論文寫作是一個動態過程。數字會修改、聲明會調整、圖表會更新——每一次變更都可能在論文其他地方留下不一致的痕跡。CRANE v0.13.0 引入完整的追溯鏈，確保每個數字都有出處、每個聲明都有支撐。

### 快速開始

在 OpenCode 中對任何 .tex 或 .pdf 檔案說：

```
trace this paper          # 英文觸發
do paper trace            # 英文觸發
整理這篇研究               # 中文觸發
```

等同執行：

```python
trace_paper(paper_path="JLE/JLE-main.tex", mode="full")
```

這會自動：
1. 建立 `_paper_trace/v1/` 目錄
2. 從論文內容推斷 RQ、貢獻聲明、實驗、評審風險
3. 生成 10 個 YAML 追溯文件
4. 在 `_paper_trace/README.md` 記錄版次

### 完整工作流範例

```python
# 1. 初始化追溯（首次）
trace_paper("00_Paper/JLE/JLE-main.tex", mode="full")
# → 建立 _paper_trace/v1/ + 推斷結構

# 2. 手動補充細節
add_research_question(
    paper_path="...",
    rq_id="RQ1",
    text="Does affect-aware training improve HCI engagement?",
    hypothesis="Yes — emotion context reduces cognitive load"
)

add_contribution(
    paper_path="...",
    contribution_id="C1",
    claim="Our model achieves 87.3% accuracy on AffectCorpus",
    strongest_defensible_wording="...under the specified train/val/test split...",
    rq_ids=["RQ1"]
)

# 3. 記錄實驗
add_experiment(
    paper_path="...",
    exp_id="E1",
    goal="Compare affect-aware vs baseline",
    dataset="AffectCorpus",
    model="AffectNet-v2",
    related_contributions=["C1"],
    related_rqs=["RQ1"]
)

# 4. 記錄變更影響
log_change(
    paper_path="...",
    change="Accuracy updated from 0.85 to 0.87 after fixing seed",
    changed_artifact="E1",
    impact_severity="high",
    must_update=[
        {"artifact": "Fig:3", "artifact_type": "figure", "reason": "Bar chart values changed"},
        {"artifact": "Table:2", "artifact_type": "table", "reason": "Main results table"},
        {"artifact": "Sec:4", "artifact_type": "section", "reason": "Inline text: '85%'"},
    ]
)

# 5. 查看待辦更新
get_pending_changes(paper_path="...")
# → [{change_id: "CH001", artifact: "Fig:3", status: "pending"}, ...]

# 6. 確認完成
mark_change_resolved(paper_path="...", change_id="CH001", artifact="Fig:3")

# 7. 生成 Mermaid 可視化
get_traceability_mermaid(paper_path="...")
# → flowchart LR
#     RQ1["RQ1: Does affect..."]:::rq
#     C1["C1: 87.3% accuracy"]:::contribution
#     E1["E1: AffectNet vs baseline"]:::experiment
#     RQ1 --> C1 --> E1

# 8. 生成需求追溯矩陣（投稿用）
generate_rtm(paper_path="...", output_path="rtm.md")
```

### 掃描工作區所有論文

```python
list_active_papers(search_root="00_Paper/")
# →
# JLE/         ← has_trace: true,  trace_version: 3
# ESWA/        ← has_trace: false  (尚未追溯)
# TKDE/        ← has_trace: true,  trace_version: 1
# TNNLS-nogo/  ← 自動跳過（含 nogo 關鍵字）
```

### 版本比對

```python
diff_trace_versions(paper_path="...", version_a=1, version_b=3)
# → delta: {rq_count: +0, contribution_count: +1, experiment_count: +2,
#           chain_coverage: +0.35, pending_changes: -3}
```

### 24 個追溯工具

| 工具 | 功能 |
|------|------|
| `trace_paper` | 主入口：init + infer + status + viz 四種模式 |
| `list_active_papers` | 掃描工作區，跳過廢棄論文 |
| `init_traceability` | 建立空白版次（不推斷） |
| `get_traceability_status` | 查看鏈完整性（唯讀） |
| `add_research_question` | 新增 RQ 到 6_research_question.yaml |
| `add_contribution` | 新增貢獻到 1_contribution.yaml |
| `add_experiment` | 新增實驗到 2_experiment.yaml |
| `add_figure_table` | 新增圖表到 5_figure_table_map.yaml |
| `add_trace_reference` | 新增引用放置規則到 4_citation_map.yaml |
| `add_reviewer_risk` | 新增評審風險到 8_limitation_reviewer_risk.yaml |
| `add_dataset` | 新增資料集到 9_dataset_baseline_protocol.yaml |
| `add_baseline` | 新增 baseline 到 9_dataset_baseline_protocol.yaml |
| `link_artifacts` | 新增產物到 10_artifact_index.yaml |
| `log_change` | 記錄變更 + 自動生成 CH{n} ID |
| `get_change_impact` | 查看特定變更的影響範圍 |
| `get_pending_changes` | 列出所有待完成的更新項目 |
| `mark_change_resolved` | 標記項目已完成 |
| `verify_traceability_chain` | 驗證 RQ→貢獻→實驗→圖表完整性 |
| `find_orphan_artifacts` | 找出沒有連接的孤立節點 |
| `generate_artifact_index` | 生成追溯摘要索引 |
| `get_traceability_mermaid` | 生成 Mermaid 流程圖（顏色編碼） |
| `get_traceability_dot` | 生成 Graphviz DOT 圖 |
| `diff_trace_versions` | 比較兩個版次的差異 |
| `generate_rtm` | 生成需求追溯矩陣（Markdown） |

---

## 核心特性版本總覽

### 🏆 v0.13.0（本版）：論文可追溯性系統

| 特性 | 實現 | 代碼量 | 測試 |
|------|------|--------|------|
| **模型層** | TraceabilityIndex + 18 個 dataclass | 410 行 | ✅ 73 個 |
| **圖引擎** | ImpactGraphService（鄰接表，無外部依賴） | ~175 行 | ✅ |
| **核心服務** | TraceabilityService（5 層路徑回退、版次管理） | ~430 行 | ✅ |
| **可視化** | TraceabilityVizService（Mermaid + DOT） | ~160 行 | ✅ |
| **推斷引擎** | TraceabilityInferenceService（正則啟發式提取） | ~220 行 | ✅ |
| **MCP 工具** | 24 個工具 in traceability.py | ~600 行 | ✅ 50 個 |
| **YAML 模板** | 10 個追溯模板 | — | — |
| **LLM 模板** | 4 個推斷提示模板 | — | — |

**v0.13.0 總計**：~2,000 行新增代碼 + 123 個新測試（100% 通過）

### 🔥 v0.12.2：Feynman 整合（Issues #71-#72）

| 特性 | 實現 | 代碼量 | 測試 |
|------|------|--------|------|
| **證據導向編排器** | EvidenceOrchestrator | 330 行 | ✅ 15 個 |
| **多來源證據收集器** | MultiSourceEvidenceCollector | 365 行 | ✅ 22 個 |

**v0.12.2 總計**：695 行 + 37 個測試

### 🚀 v0.12.0：4 個研究缺口解決方案（Issues #59-#62）

| 特性 | 實現 | 代碼量 | 測試 |
|------|------|--------|------|
| **論文-程式碼對齊驗證** | PaperCodeAlignmentService | 641 行 | ✅ 13 個 |
| **研究管道基準評估** | ResearchPipelineBenchmarkService | 522 行 | ✅ 16 個 |
| **AI 輔助信任校準** | TrustCalibrationService | 521 行 | ✅ 18 個 |
| **MCP 工具編排** | MCPToolOrchestrationService | 704 行 | ✅ 19 個 |

**v0.12.0 總計**：2,388 行 + 66 個測試

### 🏆 v0.11.0：6 個研究階段完整實現

| 特性 | 實現 | 代碼量 | 測試 |
|------|------|--------|------|
| **實驗生成** | ExperimentGenerationService | 570 行 | ✅ |
| **想法生成** | IdeationService | 385 行 | ✅ |
| **自動評審** | AutomatedReviewerV2 | 328 行 | ✅ 29 個 |
| **期刊匹配** | DynamicJournalMatchingService | 343 行 | ✅ 18 個 |
| **因果推理** | CausalReasoningEngine | 444 行 | ✅ 27 個 |
| **多輪優化** | IterativePaperOptimizationOrchestrator | 388 行 | ✅ 30 個 |

---

## 快速開始

### 一行安裝

```bash
curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash
```

安裝腳本會自動完成：git clone、uv sync、bun plugin 安裝、OpenCode 設定、SKILL.md 部署。

### 手動安裝

```bash
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
cd ~/.opencode-crane && uv sync

# 設定 OpenCode
mkdir -p ~/.config/opencode
cat > ~/.config/opencode/opencode.json << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["sh", "-c", "cd ~/.opencode-crane && uv run crane"],
      "enabled": true
    }
  }
}
EOF
```

### 前置需求

- **Python**: 3.10+
- **uv**: [安裝指引](https://astral.sh/uv/install.sh)
- **作業系統**：Linux (Ubuntu 20.04+) 或 macOS

### 驗證安裝

```bash
uv run pytest tests/ -m "not integration" -q
# 應看到：2100+ passed
```

---

## 功能對比

| 特性 | CRANE | Zotero | Mendeley | Obsidian |
|------|-------|--------|----------|----------|
| **AI 自主性** | 121 個 MCP 工具 | 第三方插件 | 有限 | 手動設置 |
| **實驗生成** | ✅ 代碼合成、超參優化 | ✗ | ✗ | ✗ |
| **想法生成** | ✅ Map Elites、Pareto | ✗ | ✗ | ✗ |
| **自動評審** | ✅ 5 評審員集合 | ✗ | ✗ | ✗ |
| **期刊趨勢** | ✅ 實時排名、動態推薦 | ✗ | ✗ | ✗ |
| **因果推理** | ✅ 8 框架統一 API | ✗ | ✗ | ✗ |
| **多輪優化** | ✅ 自動循環協調 | ✗ | ✗ | ✗ |
| **🆕 論文追溯** | ✅ 10 文件完整控制鏈 | ✗ | ✗ | ✗ |
| **🆕 變更影響** | ✅ 自動 CH{n} 追蹤 | ✗ | ✗ | ✗ |
| **開發者友善** | CLI/MCP/YAML | GUI 重 | GUI 重 | 筆記重 |

---

## 版本歷史

| 版本 | 發佈日期 | 重點 |
|------|----------|-------|
| **v0.13.0** | 2026-04-14 | 論文可追溯性系統：24 個工具、4 個服務、10 YAML 模板、123 個測試。自然語言觸發「trace this paper」/ 「整理這篇研究」。 |
| **v0.12.2** | 2026-04-10 | Feynman 整合（Issues #71-#72）：EvidenceOrchestrator + MultiSourceEvidenceCollector。695 行 + 37 個測試 |
| **v0.12.1** | 2026-04-07 | 版本同步與文件增強 |
| **v0.12.0** | 2026-04-07 | 4 個研究缺口：論文-程式碼對齊（#59）、管道基準（#60）、信任校準（#61）、MCP 工具編排（#62）。2,388 行 + 66 個測試 |
| v0.11.0 | 2026-04-06 | 6 個研究階段完整實現：實驗生成、想法生成、自動評審、期刊匹配、因果推理、多輪優化 |
| v0.10.1 | 2026-04-06 | 期刊感知寫作風格工具包：55 本期刊、8 項量化指標 |
| v0.10.0 | 2026-04-06 | ACM TOSEM 投稿工具鏈 |
| v0.9.x | 2026-04-04 | LeCun 框架、代理管理、紙碼一致性 |

---

## 開發與測試

### 環境設置

```bash
cd ~/.opencode-crane
uv sync --dev
```

### 運行測試

```bash
# 單元測試（推薦）
uv run pytest tests/ -m "not integration" -q

# 含覆蓋率
uv run pytest tests/ --cov=crane --cov-report=term-missing

# 特定模組
uv run pytest tests/tools/test_traceability_tools.py -v
uv run pytest tests/models/test_traceability.py -v
```

### 新增工具

1. 在 `src/crane/services/` 建立服務
2. 在 `src/crane/tools/` 建立工具模組，匯出 `register_tools(mcp)`
3. 在 `src/crane/server.py` 匯入並呼叫
4. 更新 `scripts/install.sh` 的 `EXPECTED_TOOLS`

### 專案結構

```
src/crane/
  server.py                  # FastMCP 入口；匯入並註冊所有工具
  tools/                     # 工具模組（每個匯出 register_tools）
    traceability.py          # 🆕 v0.13.0：24 個追溯工具
    evaluation_v2.py         # 評估工具（5 個）
    pipeline.py              # 工作流管道（含 paper-trace）
    workspace.py             # 工作區工具（含追溯能力偵測）
    [其他 26 個工具模組]
  services/                  # 業務邏輯服務
    traceability_service.py       # 🆕 核心追溯服務（版次管理）
    impact_graph_service.py       # 🆕 鄰接表圖引擎
    traceability_viz_service.py   # 🆕 Mermaid + DOT 可視化
    traceability_inference_service.py  # 🆕 正則啟發式推斷
    evidence_orchestrator_service.py   # v0.12.2
    experiment_generation_service.py   # v0.11.0
    [其他 50+ 個服務]
  models/
    traceability.py          # 🆕 18 個 dataclass（RQ、貢獻、實驗等）
    paper_profile.py
    [其他模型]
  config/
    templates/
      traceability/          # 🆕 10 個 YAML 模板（空白初始結構）
    journal_standards/       # 55 本 Q1 期刊設定
  templates/
    llm/                     # LLM 提示模板
      traceability_extract_rq.txt          # 🆕
      traceability_extract_contribution.txt # 🆕
      traceability_extract_experiment.txt   # 🆕
      traceability_extract_risk.txt         # 🆕

tests/
  models/
    test_traceability.py     # 🆕 73 個模型測試
  tools/
    test_traceability_tools.py  # 🆕 50 個工具測試
    test_claude_usability.py    # 工作流發現測試
  services/                  # 200+ 服務單元測試
  integration/               # 整合測試
```

---

## 實際應用案例

### 1️⃣ 新論文：從想法到追溯鏈

```bash
# 建立專案並開始追溯
init_research(field="HCI", type="full-research")
trace_paper("00_Paper/JLE/JLE-main.tex", mode="full")
# → _paper_trace/v1/ 自動建立，RQ/貢獻/實驗/風險 自動推斷
```

### 2️⃣ 修改實驗數字後的影響追蹤

```python
# 實驗結果更新
log_change(
    paper_path="JLE/JLE-main.tex",
    change="Accuracy 0.85 → 0.87 (fixed random seed)",
    changed_artifact="E1",
    impact_severity="high",
    must_update=[
        {"artifact": "Fig:3", "artifact_type": "figure", "reason": "Bar chart"},
        {"artifact": "Table:2", "artifact_type": "table", "reason": "Main results"},
        {"artifact": "Sec:5", "artifact_type": "section", "reason": "Inline claim '85%'"},
    ]
)

# 查看待更新項目
get_pending_changes(paper_path="JLE/JLE-main.tex")
```

### 3️⃣ 投稿前完整性檢查

```python
# 驗證完整追溯鏈
verify_traceability_chain(paper_path="...")
# → {rq_coverage: 1.0, contribution_coverage: 0.8, orphans: ["E3"]}

# 生成需求追溯矩陣
generate_rtm(paper_path="...", output_path="submission/rtm.md")

# 7 維度品質評估
evaluate_paper_v2(paper_path="main.tex")
match_journal_v2(paper_path="main.tex", budget_usd=3000)
```

### 4️⃣ 多論文工作區管理

```python
list_active_papers(search_root="00_Paper/")
# → JLE/ (v3), ESWA/ (未追溯), TKDE/ (v1)
# → TNNLS-nogo/ 自動跳過

diff_trace_versions(paper_path="JLE/main.tex", version_a=1, version_b=3)
# → chain_coverage: 0.40 → 0.95 (+0.55)
```

---

## 引用

如果 CRANE 對您的研究有幫助，請引用：

```bibtex
@software{crane2026,
  author  = {Chao, August and contributors},
  title   = {CRANE: Autonomous Research Assistant System},
  year    = {2026},
  url     = {https://github.com/AugustChaoTW/opencode-crane},
  note    = {121 MCP tools for end-to-end research automation, aligned with Nature's The AI Scientist}
}
```

---

## 授權

MIT 授權 — 詳見 [LICENSE](LICENSE) 檔案

---

## 支援與反饋

- **GitHub Issues**: [報告問題](https://github.com/AugustChaoTW/opencode-crane/issues)
- **Discussions**: [功能建議與討論](https://github.com/AugustChaoTW/opencode-crane/discussions)
- **Community**: [OpenCode 社群](https://github.com/anomalyco/opencode)

---

**立即開始**：執行安裝腳本，然後對任一論文說 `trace this paper`！
