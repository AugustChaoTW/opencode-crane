# CRANE：自主科學研究助理系統

> AI 驅動的端到端研究自動化——從第一篇文獻到論文投稿的完整工作流程。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Server](https://img.shields.io/badge/MCP-Server-orange.svg)](https://modelcontextprotocol.io/)
[![Version](https://img.shields.io/badge/version-0.14.5-green.svg)](https://github.com/AugustChaoTW/opencode-crane/releases)

**124 個 MCP 工具**，涵蓋從文獻回顧到期刊投稿的 7 個研究階段。  
CRANE provides **124 MCP Tools** for end-to-end academic research automation.  
基於 Nature《The AI Scientist》的研究架構，並整合 Karpathy 4 原則作為 AI 寫程式的品質守門。

---

## CRANE 是什麼？

CRANE 是一個跑在 [OpenCode](https://github.com/anomalyco/opencode) 上的 **MCP 伺服器**。你在聊天框中說話，CRANE 在背後呼叫工具、讀寫你的研究資料夾、回傳結果。

**不是摘要器，是研究夥伴。** 它記得你的文獻、追蹤你的實驗、在投稿前幫你做自動評審。

```
你 → OpenCode → CRANE MCP → 你的 references/ 資料夾
                           → GitHub Issues（任務追蹤）
                           → _paper_trace/（論文追溯）
                           → 期刊標準資料庫（55 本 Q1）
```

---

## 七個研究階段與使用情境

### 第 1 階段：文獻搜索與回顧

**你在做什麼**：從零開始建立文獻庫，或補充現有研究的相關文獻。

**典型對話**：

```
# 搜尋 arXiv 新論文
search_papers("affect recognition transformer 2024")

# 搜尋本地文獻庫
search_references("emotion detection multimodal")

# 下載 PDF 並自動解析後設資料
download_paper("https://arxiv.org/abs/2401.xxxxx")

# 建立 embedding（OpenAI 或本機 Ollama）
build_embeddings()                             # OpenAI text-embedding-3-small
build_embeddings(provider="ollama")            # 本機 nomic-embed-text，免 API key

# 語意搜尋——找跟某篇論文最相近的其他論文
semantic_search(anchor_paper_key="vaswani2017attention", k=10)

# 建立引用關係圖，找出你遺漏的重要論文
build_citation_graph()
find_citation_gaps()

# 用 PICOS 框架系統化篩選論文
screen_papers_by_picos(
    population="HCI users",
    intervention="affect-aware interface",
    comparison="traditional interface",
    outcome="engagement",
    study_type="experiment"
)
```

**產出**：
- `references/papers/` — 每篇論文的 YAML 後設資料
- `references/pdfs/` — PDF 原文
- `references/bibliography.bib` — 隨時可用的 BibTeX

---

### 第 2 階段：論文評估與位置校準

**你在做什麼**：決定哪些論文值得精讀，你的研究在學術地景中的定位。

**典型對話**：

```
# 7 維度深度評估單篇論文（方法論、新穎性、可重現性…）
evaluate_paper_v2(paper_key="zhang2023affect")

# 評估是否符合 Q1 期刊標準
evaluate_q1_standards(paper_key="zhang2023affect", journal="IEEE TPAMI")

# 分析你的研究在學術地景的位置
analyze_research_positioning(
    your_contribution="affect-aware training with sparse labels",
    domain="HCI"
)

# 產生 Feynman 教學摘要——用最簡單的話解釋核心概念
generate_feynman_session(paper_key="vaswani2017attention")

# 語意分群——看文獻庫的主題分布
get_research_clusters(k_clusters=5)
visualize_citations(mode="clusters", output_format="mermaid")
```

**產出**：
- 7 維度評分報告（寫作 12%、方法論 18%、新穎性 18%、評估 20%、呈現 8%、局限 10%、可重現 14%）
- 競爭對手地圖
- 引用關係視覺化（Mermaid / 圖檔）

---

### 第 3 階段：實驗設計與執行管理

**你在做什麼**：設計實驗、追蹤執行狀態、確保結果可重現。

**典型對話**：

```
# 在開始寫程式之前，先讓 CRANE 幫你想清楚
plan_experiment_implementation(
    "實作 affect-aware loss function，加入稀疏標籤的正則化"
)

# 定義可驗證的成功標準（不要模糊說「改善準確率」）
define_experiment_success_criteria(
    goal="在 AffectCorpus 上比 BERT baseline 高 3% F1",
    domain="experiment"
)

# 把實驗加進論文追溯系統
trace_add(
    paper_path="papers/JLE/main.tex",
    item_type="experiment",
    item_id="E1",
    data={
        "goal": "比較 affect-aware 與 baseline 在 AffectCorpus 的 F1",
        "dataset": "AffectCorpus",
        "model": "AffectNet-v2",
        "hardware": "RTX 4090 × 2",
        "related_contributions": ["C1"],
        "related_rqs": ["RQ1"]
    }
)

# 實驗跑完，記錄變更並追蹤下游影響
log_change(
    paper_path="papers/JLE/main.tex",
    change="E1 重新跑，F1 從 0.847 改為 0.863（修正 seed）",
    why="seed 設定錯誤導致不可重現",
    changed_artifact="E1",
    impact_severity="high",
    must_update=[
        {"artifact": "Fig:1", "reason": "圖中數字需更新"},
        {"artifact": "T:1", "reason": "表格數字需更新"}
    ]
)
```

**產出**：
- 可驗證的實驗計劃（假設、成功標準、反向目標）
- `_paper_trace/v{n}/2_experiment.yaml` — 正規化實驗記錄
- `_paper_trace/v{n}/7_change_log_impact.yaml` — 變更影響鏈

---

### 第 4 階段：想法生成與研究貢獻定義

**你在做什麼**：找出研究缺口，強化貢獻聲明，應對 reviewer 挑戰。

**典型對話**：

```
# 解構領域常識——找出「大家都這樣說但沒人驗證」的假設
deconstruct_conventional_wisdom(
    claim="Transformer 在情感識別上優於 CNN",
    domain="affect recognition"
)

# 把貢獻聲明寫得更精確、更可辯護
trace_add(
    paper_path="papers/JLE/main.tex",
    item_type="contribution",
    item_id="C1",
    data={
        "claim": "本研究提出 AffectNet-v2，在 AffectCorpus 達到 86.3% F1，比最強 baseline（BERT-base）高 3.2%",
        "why_it_matters": "稀疏標籤場景下的情感識別性能瓶頸",
        "strongest_defensible_wording": "在 AffectCorpus 測試集，條件 X 下，F1=0.863",
        "reviewer_risk": "Reviewer 可能質疑 baseline 選擇",
        "response_strategy": "Table 2 已包含 GPT-4 比較；見 Appendix B"
    }
)

# 加入 reviewer 風險管理
trace_add(
    paper_path="papers/JLE/main.tex",
    item_type="risk",
    item_id="R1",
    data={
        "description": "Reviewer 2 可能說 AffectCorpus 太小（10K 樣本）",
        "severity": "high",
        "likely_appears_in": "Reviewer 2",
        "response_strategy": "引用 Li et al. (2023) 的 12K 樣本研究；說明標籤稀疏性是特色",
        "fallback_claim": "本研究聚焦稀疏標籤場景，不比較全監督"
    }
)
```

**產出**：
- 強化後的貢獻聲明（最強可辯護措辭）
- Reviewer 風險清單 + 回應策略
- `_paper_trace/v{n}/1_contribution.yaml`
- `_paper_trace/v{n}/8_limitation_reviewer_risk.yaml`

---

### 第 5 階段：論文寫作與風格校準

**你在做什麼**：按目標期刊的風格寫作，診斷各章節偏差，生成改寫建議。

**典型對話**：

```
# 診斷整篇論文（所有章節）的風格偏差
crane_diagnose(
    paper_path="papers/JLE/main.tex",
    journal_name="IEEE TPAMI",
    scope="paper"
)

# 只診斷 Introduction 章節
crane_diagnose(
    paper_path="papers/JLE/main.tex",
    journal_name="IEEE TPAMI",
    scope="section",
    section_name="Introduction"
)

# 產生具體改寫建議
crane_suggest_rewrites(
    paper_path="papers/JLE/main.tex",
    section_name="Introduction",
    journal_name="IEEE TPAMI",
    count=5
)

# 比較兩個期刊的風格差異（決定改投哪裡）
crane_compare_sections(
    paper_path="papers/JLE/main.tex",
    section_name="Methods",
    journal1="IEEE TPAMI",
    journal2="ACM TOSEM"
)

# 查看章節結構是否符合追溯鏈要求
review_paper_sections(paper_path="papers/JLE/main.tex")
```

**產出**：
- 各章節偏差分數（越低越接近目標期刊風格）
- 逐句改寫建議（支援互動選擇）
- 章節完整性報告（引用是否在對的位置）

---

### 第 6 階段：自動評審與期刊匹配

**你在做什麼**：投稿前的最終品質把關，找最適合的期刊。

**典型對話**：

```
# 5 位虛擬 reviewer 集合評審（含元評審）
evaluate_paper_v2(paper_path="papers/JLE/main.tex")

# 從 55 本 Q1 期刊中找最佳匹配
match_journal_v2(paper_path="papers/JLE/main.tex")

# 深入分析某本期刊的適配度
analyze_paper_for_journal(
    paper_path="papers/JLE/main.tex",
    journal_name="IEEE TPAMI"
)

# APC 費用分析（開放取用費用）
analyze_apc(journal_name="IEEE TPAMI")

# 產生投稿 cover letter
crane_generate_cover_letter(
    paper_path="papers/JLE/main.tex",
    journal_name="IEEE TPAMI"
)

# 模擬投稿結果（接受/修改/拒稿機率）
simulate_submission_outcome(
    paper_path="papers/JLE/main.tex",
    journal_name="IEEE TPAMI"
)

# 完整投稿流程自動化
crane_journal_workflow_auto(
    paper_path="papers/JLE/main.tex",
    journal_name="IEEE TPAMI"
)
```

**產出**：
- 5 評審員報告 + 元評審結論
- 期刊排名（5 維度加權：範圍 35%、貢獻風格 20%、評估風格 20%、引用 15%、運營 10%）
- Cover letter 草稿
- 投稿風險評估（accept / major revision / reject 各機率）

---

### 第 7 階段：論文可追溯性系統

**你在做什麼**：確保整篇論文的聲明、數字、圖表、引用都一致，有任何變更立刻知道影響範圍。

**典型對話**：

```
# 第一次使用：一鍵初始化追溯系統（自動從論文推斷結構）
trace_paper(
    paper_path="papers/JLE/main.tex",
    mode="full"
)
# 或直接說：trace this paper / 整理這篇研究

# 查看追溯鏈完整性
get_traceability_status(paper_path="papers/JLE/main.tex")

# 確認所有鏈結都完整（RQ → 貢獻 → 實驗 → 圖表）
verify_traceability_chain(paper_path="papers/JLE/main.tex")

# 找出沒有上下游連接的孤立節點
find_orphan_artifacts(paper_path="papers/JLE/main.tex")

# 某個實驗數字改了，看影響哪些地方
get_change_impact(
    paper_path="papers/JLE/main.tex",
    artifact_id="E1"
)

# 查看還有哪些東西需要更新
get_pending_changes(paper_path="papers/JLE/main.tex")

# 產生 Requirements Traceability Matrix（RTM）給 journal editor
generate_rtm(paper_path="papers/JLE/main.tex")

# 視覺化整個追溯圖（Mermaid 格式，可貼到 GitHub）
get_traceability_viz(
    paper_path="papers/JLE/main.tex",
    output_format="mermaid"
)

# 比較兩個版本的差異
diff_trace_versions(
    paper_path="papers/JLE/main.tex",
    version_a=1,
    version_b=2
)
```

**追溯文件結構**（自動建立於 `_paper_trace/v{n}/`）：

| 文件 | 記錄內容 |
|------|---------|
| `1_contribution.yaml` | 貢獻聲明 + 最強可辯護措辭 |
| `2_experiment.yaml` | 實驗設置 + 正規化結果數字 |
| `3_section_outline.yaml` | 各章節必寫／禁寫事項 |
| `4_citation_map.yaml` | 引用出現規則（哪個引用必須在哪章） |
| `5_figure_table_map.yaml` | 圖表數字 + 更新觸發條件 |
| `6_research_question.yaml` | 研究問題（全鏈起點） |
| `7_change_log_impact.yaml` | 變更記錄 + 下游影響清單 |
| `8_limitation_reviewer_risk.yaml` | 評審風險 + 回應策略 |
| `9_dataset_baseline_protocol.yaml` | 資料集 + baseline 可重現規則 |
| `10_artifact_index.yaml` | 所有追蹤文件（腳本、模型、圖表） |

---

### Karpathy 4 原則工具（v0.14.0 新增）

**你在做什麼**：在 AI 幫你生成程式碼或實驗計劃之前，先做品質把關。

```
# 原則 1：先想清楚再寫——產生實作計劃
plan_experiment_implementation(
    "在訓練迴圈中加入 affect-aware loss，使用稀疏標籤正則化"
)

# 原則 2：檢查是否過度複雜
check_code_simplicity(code=open("train.py").read())

# 原則 3：確認修改是否精準（沒有動到不相關的程式碼）
review_code_changes(
    original=old_code,
    modified=new_code,
    stated_goal="修正 seed 設定"
)

# 原則 4：把模糊目標轉成可驗證的成功標準
define_experiment_success_criteria(
    goal="改善 AffectCorpus 準確率",
    domain="experiment"
)

# 全部 4 原則一次跑
karpathy_review(
    code=generated_code,
    original_code=original,
    stated_goal="implement affect loss",
    domain="experiment"
)
```

---

## 快速開始

### 安裝

```bash
# 從 PyPI 安裝（推薦）
pip install opencode-crane

# 或從原始碼安裝
git clone https://github.com/AugustChaoTW/opencode-crane
cd opencode-crane
uv sync
```

### 設定 OpenCode

在 `~/.opencode/mcp.json` 加入：

```json
{
  "servers": {
    "crane": {
      "command": "crane",
      "env": {
        "GH_TOKEN": "your_github_token"
      }
    }
  }
}
```

### 初始化研究工作區

```bash
# 建立標準資料夾結構
init_research(project_name="my-research")

# 確認工作區狀態
workspace_status()

# 檢查某個工具的前置條件
check_prerequisites("semantic_search")
```

### 環境變數

| 變數 | 必要 | 用途 |
|------|------|------|
| `GH_TOKEN` | 必要 | GitHub Issues 任務追蹤 |
| `OPENAI_API_KEY` | 選用 | 語意搜尋 embedding（OpenAI 路徑） |
| `CRANE_CHECK_VERSION_ON_START` | 選用（預設 true） | 啟動時檢查更新 |

> **不想用 OpenAI？** v0.14.4 支援本機 Ollama embedding，完全不需要 API key：
>
> ```bash
> ollama pull nomic-embed-text        # 274 MB，768 維向量
> ```
> ```
> build_embeddings(provider="ollama")                          # 預設 nomic-embed-text
> build_embeddings(provider="ollama", model="mxbai-embed-large")  # 1024 維
> ```

> **想用 OpenRouter？** v0.14.5 支援 OpenRouter 許可規則分析：
> ```bash
> export OPENROUTER_API_KEY="sk-or-v1-..."
> ```
> ```
> critique_permission_rules(model="openrouter/elephant-alpha")
> ```

---

## 工具總覽（124 個）

### 文獻管理
`search_papers` · `search_references` · `download_paper` · `add_reference` · `get_reference` · `list_references` · `remove_reference` · `annotate_reference` · `verify_reference` · `check_citations` · `check_all_references` · `read_paper` · `parse_paper_structure`

### 語意搜尋
`semantic_search` · `build_embeddings` · `chunk_papers` · `ask_library` · `get_chunk_stats`

### 引用圖分析
`build_citation_graph` · `find_citation_gaps` · `get_research_clusters` · `visualize_citations`

### 論文篩選
`screen_papers_by_picos` · `screen_reference` · `list_screened_references` · `compare_papers`

### 論文評估
`evaluate_paper_v2` · `evaluate_q1_standards` · `review_paper_sections` · `analyze_paper_for_journal` · `match_journal_v2` · `generate_feynman_session` · `deconstruct_conventional_wisdom` · `analyze_research_positioning`

### 論文可追溯性（第 7 階段）
`trace_paper` · `init_traceability` · `trace_add` · `link_artifacts` · `log_change` · `get_change_impact` · `get_pending_changes` · `mark_change_resolved` · `verify_traceability_chain` · `find_orphan_artifacts` · `get_traceability_status` · `get_traceability_viz` · `diff_trace_versions` · `generate_rtm` · `generate_artifact_index` · `list_active_papers`

### 期刊投稿
`crane_journal_setup` · `crane_journal_questionnaire` · `crane_assess_risk` · `crane_generate_cover_letter` · `crane_get_journal_workflow_status` · `crane_journal_workflow_auto` · `run_submission_check` · `simulate_submission_outcome` · `generate_submission_checklist` · `analyze_apc` · `find_similar_papers_in_journal`

### 寫作風格
`crane_diagnose` · `crane_suggest_rewrites` · `crane_compare_sections` · `crane_start_rewrite_session` · `crane_submit_rewrite_choice` · `crane_get_rewrite_session` · `crane_list_rewrite_sessions` · `crane_coach_chapter` · `crane_export_style_report` · `crane_extract_journal_style_guide` · `crane_get_style_exemplars` · `crane_get_user_preferences` · `crane_reset_user_preferences` · `crane_review_full`

### Karpathy 4 原則（v0.14.0）
`plan_experiment_implementation` · `check_code_simplicity` · `review_code_changes` · `define_experiment_success_criteria` · `karpathy_review`

### 實驗設計
`generate_figure` · `generate_comparison` · `generate_revision_report` · `benchmark_research_pipeline`

### 任務追蹤
`create_task` · `update_task` · `close_task` · `view_task` · `list_tasks` · `report_progress` · `get_milestone_progress`

### 系統與工作區
`init_research` · `workspace_status` · `check_prerequisites` · `list_workflows` · `run_pipeline` · `get_project_info` · `check_crane_version` · `upgrade_crane` · `rollback_crane` · `orchestrate_research_tools`

### Transport / Session
`transport_control` · `broadcast_sse_event` · `create_session` · `save_session` · `load_session` · `list_sessions` · `delete_session` · `generate_bridge_jwt`

### Agent 管理
`get_agent` · `list_agents` · `add_agent_memory` · `get_agent_memory` · `clear_agent_memory`

### 權限與信任
`add_permission_rule` · `remove_permission_rule` · `list_permission_rules` · `evaluate_permission_action` · `show_effective_rules` · `critique_permission_rules` · `calibrate_trust`

---

## 常見工作流程

### 「我剛開始做一個新研究」

```
1. init_research("my-project")
2. search_papers("your topic 2024")
3. build_embeddings()                             # OpenAI（需 API key）
   # 或：build_embeddings(provider="ollama")      # 本機 Ollama，免費
4. get_research_clusters()
5. trace_paper(paper_path="paper.tex", mode="full")
```

### 「我要投稿了，確認論文品質」

```
1. verify_traceability_chain(paper_path)   ← 確認邏輯鏈完整
2. get_pending_changes(paper_path)         ← 確認沒有未更新項目
3. evaluate_paper_v2(paper_path)           ← 5 評審員評估
4. match_journal_v2(paper_path)            ← 找最佳期刊
5. crane_journal_workflow_auto(paper_path) ← 完整投稿流程
```

### 「實驗數字改了，影響哪些地方？」

```
1. log_change(paper_path, change="E1 F1 改成 0.863", ...)
2. get_pending_changes(paper_path)
3. get_change_impact(paper_path, artifact_id="E1")
4. verify_traceability_chain(paper_path)
```

### 「AI 幫我寫了程式碼，先做品質檢查」

```
1. plan_experiment_implementation(task)
2. check_code_simplicity(code)
3. review_code_changes(original, modified, stated_goal)
4. define_experiment_success_criteria(goal)
```

---

## 版本歷史

| 版本 | 工具數 | 主要功能 |
|------|--------|---------|
| **v0.14.6** | ~130 | 3LLM 論文閱讀流程（Scanner → Extractor → Reviewer）；LLM Judge Reliability Inspector；Generalization Benchmark；RAG Test Enhancement；Label 規範與 Issue Template | 
| **v0.14.5** | 124 | OpenRouter 支援：critique_permission_rules(model="openrouter/elephant-alpha")，Elephant-Alpha 分析許可規則；空回應處理與 error handling；prompt 優化 |

---

## 已發表論文

| 標題 | 作者 | 期刊 | 狀態 |
|------|------|------|------|
| **Logic-posedness Score: A Diagnostic Framework for Identifying Adaptive Computation Failure in Spatio-Temporal Traffic Forecasting Models** | August Chao, Cheng-Yu Lai | Transportation Research Part C | Submitted (2026-04-19) |

> 本專案研究成果應用於交通預測模型的診斷框架，相關程式碼與工具有興趣可聯繫作者。 |
| **v0.14.4** | 124 | Ollama Embedding 支援：build_embeddings(provider="ollama")，本機語意搜尋不需 API key；nomic-embed-text (768d) / mxbai-embed-large (1024d)；embeddings.yaml 記錄 provider+dim，重新載入自動路由 |
| **v0.14.3** | 124 | crane_help 工具 + SKILL.md 全面改寫：觸發語意對應、Paper Trace 完整流程文件 |
| **v0.14.2** | 123 | Paper Review 結構性修正：build_paper_index、run_review_pipeline；lru_cache 快取、review_paper() 呼叫 2→1（理論加速，真實論文基準測試待補）|
| **v0.14.1** | 121 | 工具整合重構（-17 工具）：trace_add、crane_diagnose、transport_control、visualize_citations、get_traceability_viz |
| **v0.14.0** | 138 | Karpathy 4 原則工具：plan_experiment_implementation、check_code_simplicity、review_code_changes、define_experiment_success_criteria、karpathy_review |
| **v0.13.0** | 133 | 論文可追溯性系統（Paper Traceability）：24 工具、10 YAML 模板、版次管理 |
| **v0.12.2** | 109 | Feynman 整合：EvidenceOrchestrator + MultiSourceEvidenceCollector |
| **v0.12.1** | 109 | 版本同步與文件強化 |
| **v0.12.0** | 109 | 寫作風格工具包（Phase C + D）：55 本期刊風格資料庫 |
| **v0.11.0** | 95  | 動態期刊匹配、趨勢監控、APC 分析 |
| **v0.10.0** | 80  | AutomatedReviewerV2：5 評審員集合 + 元評審 |

---

## 架構

```
MCP Client（OpenCode）
    │
    ▼
src/crane/server.py          ← FastMCP over stdio
    │
    ▼
src/crane/tools/             ← 工具模組（各自 export register_tools）
    │
    ▼
src/crane/services/          ← 商業邏輯（52+ 服務類別）
    │
    ├── TraceabilityService         第 7 階段核心
    ├── AutomatedReviewerV2         5 評審員集合（~11K 行）
    ├── KarpathyReviewService       4 原則品質守門
    ├── WritingStyleService         風格診斷與改寫
    ├── DynamicJournalMatchingService  55 本期刊動態排名
    ├── ExperimentGenerationService    實驗合成（~570 行）
    └── CausalReasoningEngine          8 個 LeCun 因果框架
    │
    ▼
src/crane/providers/         ← 文獻來源適配器（arXiv、OpenAlex、Semantic Scholar…）
src/crane/models/            ← 資料結構（Paper、TraceabilityNode、CanonicalNumber…）
src/crane/config/            ← 期刊標準、領域規範、LLM prompt 模板
```

---

## 開發

```bash
# 安裝開發依賴
uv sync --dev

# 執行單元測試
uv run pytest -m "not integration" -q

# 執行整合測試
uv run pytest -m "integration"

# Lint
uv run ruff check src/ tests/

# 啟動伺服器（測試用）
crane
```

---

## 引用

```bibtex
@software{crane2025,
  title   = {CRANE: Autonomous Research Assistant MCP Server},
  author  = {AugChao},
  year    = {2025},
  url     = {https://github.com/AugustChaoTW/opencode-crane},
  note    = {121 MCP tools for end-to-end research automation, aligned with Nature's The AI Scientist}
}
```

---

## License

MIT © AugChao
