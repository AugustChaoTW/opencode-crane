# CRANE: 自主研究助理系統

**AI 驅動的研究助理，自動化論文寫作全流程——從文獻搜索到期刊投稿。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Server-orange.svg)](https://modelcontextprotocol.io/)

CRANE provides **107 MCP Tools** across the full research lifecycle.

---

## 30 秒了解 CRANE

CRANE 是為 [OpenCode](https://github.com/anomalyco/opencode) 構建的**自主研究助理 MCP 伺服器**，重新定義學術研究的工作流程。它不僅是一個「論文摘要器」，而是管理整個研究流程的完整系統：從多源資料庫搜索（arXiv、OpenAlex）到 GitHub Issues 任務追蹤，再到**證據優先的 Q1 期刊評估**、**個性化期刊匹配**與**互動式修改規劃**。CRANE 確保您的研究結構清晰、可追蹤、發表就緒。

---

## 5 個核心優勢

1. **證據優先的 Q1 評估**：7 維度混合評分引擎 + 閘值機制，從 LaTeX 論文中自動提取證據，而非單純關鍵字匹配
2. **個性化期刊匹配**：跨 55 本 Q1 期刊的加權適配度評分（範圍 35%、貢獻 20%、評估 20%、引用 15%、運營 10%）+ 桌面拒稿風險評估
3. **互動式修改工作流**：三層報告（計分卡 + 證據檢視 + 修改待辦清單）+ 優先級排序 + 修改前後比較
4. **PICOS 系統篩選**：自動提取人群/干預/比較/結果/研究設計，適合系統文獻綜述
5. **領域感知評估**：可插拔領域包（含 AI/ML、Cybersecurity、IoT、MIS）+ 自動檢測 + 自訂評分標準 + 評審者模擬

---

## 按論文寫作階段的功能指南

### 📚 **第一階段：文獻回顧與任務規劃**

**目標**：系統地搜索、組織、評估相關文獻

| 功能 | 工具 | 說明 |
|------|------|------|
| **初始化專案** | `init_research` | 設置 GitHub 里程碑、標籤、本地資料夾結構 |
| **多源文獻搜索** | `search_papers` | 從 arXiv、OpenAlex、alphaXiv 同時搜索，支援語義過濾 |
| **添加到文庫** | `add_reference` | 自動生成 BibTeX、YAML 元數據，同步 bibliography.bib |
| **讀取論文** | `read_paper` | 自動下載 PDF，提取全文或使用 alphaXiv 結構化摘要 |
| **系統篩選** | `screen_papers_by_picos` | 按人群/干預/比較/結果/設計自動篩選（系統綜述專用） |
| **語義搜索** | `semantic_search` | 向量相似度搜索，找出相關工作 |
| **引用圖分析** | `build_citation_graph` | 自動構建論文間引用關係，可視化研究網絡 |
| **識別文獻空白** | `find_citation_gaps` | 檢測您忽略但被多篇論文引用的重要論文 |
| **任務管理** | `create_task`, `list_tasks` | 通過 GitHub Issues 追蹤研究進度 |

**建議流程**：
```
1. 初始化專案: init_research()
2. 搜索文獻: search_papers(query="your topic", max_papers=50)
3. 批量添加: add_reference() for each paper
4. 系統篩選: screen_papers_by_picos(population="...", intervention="...")
5. 分析引用圖: build_citation_graph() → find_citation_gaps()
6. 創建任務: create_task(title="Read and summarize paper X")
```

---

### ✍️ **第二階段：論文寫作與架構規劃**

**目標**：組織想法、撰寫各章節、確保論文質量

| 功能 | 工具 | 說明 |
|------|------|------|
| **問文獻庫** | `ask_library` | 對所有參考文獻進行自然語言 Q&A，得到帶頁碼的引用 |
| **分塊管理** | `chunk_papers` | 將 PDF 分解為 ~500 字段落，啟用細粒度搜索 |
| **檢查引用完整性** | `check_citations` | 驗證論文中的每一個 `\cite{}` 都在文庫中，發現遺漏引用 |
| **驗證元數據** | `verify_reference` | 確保 DOI、年份、標題與原始論文一致 |
| **論文章節審核** | `review_paper_sections` | 檢測邏輯錯誤、資料不一致、過度聲稱、AI 寫作痕跡 |
| **研究定位分析** | `analyze_research_positioning` | 5 層次分析（文明→領域→方法→課題→操作），檢測層級錯位 |

**建議流程**：
```
1. 寫初稿 (Introduction, Related Work, Methods)
2. 檢查引用: check_citations(manuscript_path="main.tex")
3. 問文獻: ask_library(question="How do related works handle X?")
4. 審核章節: review_paper_sections(sections=["introduction", "methods"])
5. 驗證定位: analyze_research_positioning(paper_path="main.tex")
```

---

### 🔬 **第三階段：實驗設計與評估**

**目標**：設計堅實的評估，生成可重現的結果

| 功能 | 工具 | 說明 |
|------|------|------|
| **紙碼一致性驗證** | `verify_paper_code_alignment` | 比較 LaTeX 表格的聲稱與實際代碼實現（AST 級別） |
| **研究管道基準** | `benchmark_research_pipeline` | 評估完整 6 階段管道（構思→文獻→設計→實現→撰寫→投稿），預測期刊接受率 |
| **信任校準** | `calibrate_trust` | 動態調整自主程度（0-3 級），量化 AI 輸出的不確定性 |
| **工具編排** | `orchestrate_research_tools` | 跨領域工具選擇與排序（支援 ML、SE、HCI、理論、系統） |

**建議流程**：
```
1. 驗證紙碼對齐: verify_paper_code_alignment(paper_path="main.tex")
2. 基準管道: benchmark_research_pipeline(paper_path="main.tex")
3. 評估信任度: calibrate_trust(task_description="running X experiment")
```

---

### 🎯 **第四階段：論文質量評估與修改**

**目標**：達到 Q1 期刊標準，識別修改優先級

| 功能 | 工具 | 說明 |
|------|------|------|
| **7 維度評分** | `evaluate_paper_v2` | 證據優先評分：寫作(12%) + 方法論(18%) + 新穎性(18%) + 評估(20%) + 呈現(8%) + 局限(10%) + 可重現(14%) |
| **期刊匹配** | `match_journal_v2` | 跨 18 本 Q1 期刊的加權適配度評分 + 目標/備選/安全推薦 |
| **修改報告** | `generate_revision_report` | 三層報告：計分卡 + 證據檢視 + 優先級排序修改清單 |
| **Feynman 方法** | `generate_feynman_session` | 生成 30+ 探索性問題，迫使您為論文辯護 |
| **評審者模擬** | 集成在評分中 | 預測 10 種常見批評，模擬期刊決定 |
| **投稿前檢查** | `run_submission_check` | 最終 Q1 準備度評估 + 6 步自動化審查管道 |

**建議流程**：
```
1. 初步評分: evaluate_paper_v2(paper_path="main.tex")
2. 期刊推薦: match_journal_v2(paper_path="main.tex") 
3. Feynman 練習: generate_feynman_session(focus_dimensions=["methodology", "evaluation"])
4. 生成修改計劃: generate_revision_report(paper_path="main.tex")
5. 優先化修改: (按 ROI 排序，逐項改進)
6. 重新評分: evaluate_paper_v2() 檢查進度
```

---

### 🚀 **第五階段：投稿準備與策略**

**目標**：最大化期刊接受率，準備補充材料

| 功能 | 工具 | 說明 |
|------|------|------|
| **投稿結果預測** | `simulate_submission_outcome` | LeCun 世界模型推理：預測接受/修改/拒稿 + 二階效應 |
| **APC 成本分析** | `analyze_apc` | 跨 55 本期刊的預算感知排名（IEEE ~$2,800、Nature MI $11,990、JMLR 0 元） |
| **版本管理** | `check_crane_version`, `upgrade_crane` | 檢查更新、自動備份升級、版本回滾 |
| **補充材料檢查清單** | 手冊 | 代碼質量、依賴版本固定、可重現性文檔、GitHub 設置 |
| **撰寫投稿信** | 模板 | 為目標期刊定制投稿信 |
| **寫作風格診斷** | `crane_diagnose_paper` | 全文風格分析：逐章節比對目標期刊的 8 項指標偏差 |
| **互動式改寫** | `crane_start_rewrite_session` | 互動工作流：accept/reject/modify 逐條改寫建議 |
| **偏好學習** | `crane_get_user_preferences` | 跨工作階段學習您的寫作偏好，自動調整建議優先級 |

**建議流程**：
```
1. 預測結果: simulate_submission_outcome(paper_path="main.tex", target_journal="IEEE TPAMI")
2. 分析 APC: analyze_apc(paper_path="main.tex", budget_usd=3000)
3. 最終檢查: run_submission_check(paper_path="main.tex")
4. 補充材料: 
   - 整理 GitHub (README, LICENSE, dependencies)
   - 上傳到 Zenodo (創建 DOI)
   - 準備補充文件 (實驗代碼、數據、結果)
5. 投稿信: 使用個性化模板
6. 投稿!
```

---

## 完整工作流示例：從研究想法到投稿

```bash
# 1️⃣  初始化 (Week 1)
init_research(field="Machine Learning", domain="Transformers")
create_task(title="Systematic literature review on scaling laws", phase="literature_review")

# 2️⃣  文獻綜述 (Week 1-2)
search_papers(query="transformer scaling laws", max_papers=100)
add_reference(paper_id="arxiv:2001.08361")  # Chinchilla
screen_papers_by_picos(intervention="scaling", outcome="performance")
build_citation_graph()
ask_library(question="What are the key factors affecting scaling efficiency?")

# 3️⃣  撰寫初稿 (Week 2-4)
# 手動撰寫 Introduction, Related Work, Methods...
check_citations(manuscript_path="main.tex")
review_paper_sections(sections=["introduction", "methodology"])

# 4️⃣  實驗與評估 (Week 4-6)
verify_paper_code_alignment(paper_path="main.tex")
benchmark_research_pipeline(paper_path="main.tex")

# 5️⃣  質量評估與修改 (Week 6-7)
evaluate_paper_v2(paper_path="main.tex")  # 評分: 88/100
match_journal_v2(paper_path="main.tex")   # 推薦: IEEE TPAMI (目標), TNNLS (備選)
generate_revision_report(paper_path="main.tex")
# 修改: 添加消融研究 (+8 分), 補充統計顯著性測試 (+5 分)
evaluate_paper_v2(paper_path="main.tex")  # 重新評分: 92/100

# 6️⃣  投稿準備 (Week 8)
simulate_submission_outcome(paper_path="main.tex", target_journal="IEEE TPAMI")
analyze_apc(paper_path="main.tex", budget_usd=3000)
run_submission_check(paper_path="main.tex")  # 最終檢查
# 準備 GitHub、Zenodo、補充文件
```

---

## 核心特性（詳細說明）

### 🏆 **v0.10.0 新功能：ACM TOSEM 投稿完整工具鏈**

CRANE v0.10.0 添加了完整的 ACM TOSEM 期刊投稿支援工作流，包括：

#### 1. **投稿前完整檢查** (`run_submission_check`)
- 文獻回顧驗證 (40 個參考文獻檢查清單)
- 實驗數據彙總 (156 個實驗結果確認)
- 論文框架分析 (過度聲稱、薄弱論證檢測)
- 論文健康報告 (8 項檢查類別，可視化進度)

#### 2. **期刊策略與風險評估** 
- 4 維度風險評估 (Desk Reject、評審期望、寫作品質、倫理合規)
- 18 本 Q1 期刊適配度分析
- 個性化投稿信生成
- 修改追蹤與版本控制

#### 3. **集成的投稿前評估報告**
- TOSEM 期刊特定評分（Software Engineering Methods 92/100 等）
- 優先級排序改進建議 (ROI 矩陣)
- 修改時間表 (1-3 週內可完成的改進)

#### 4. **論文寫作階段模板**
- Implementation 章節模板
- Empirical Evaluation 章節模板
- Limitations & Discussion 模板
- Conclusion 模板
- 全部針對 ACM TOSEM 標準最佳化

#### 5. **效能基準與使用者評估框架**
- 性能基準方法論 (4 個核心指標)
- 使用者評估問卷 (28 題，5 個評估維度)
- 數據收集模板 (JSON/CSV)
- 競爭對手分析矩陣 (15 維度 × 5 工具對比)

#### 6. **補充材料與可重現性**
- GitHub 設置檢查清單
- 補充材料提交指南
- README 模板
- 可重現性文檔模板
- 數據可得性聲明模板

---

### 📊 **Q1 評估引擎 (v0.9.1+)**
- **7 維度混合評分**：寫作品質(12%) + 方法論(18%) + 新穎性(18%) + 評估(20%) + 呈現(8%) + 局限(10%) + 可重現(14%)
- **證據優先**：每維度提取引用跨度與推理代碼
- **閘值機制**：方法論/新穎性/評估任一維度低於 60 則阻止 Q1 認證
- **自動分類**：識別論文類型（實驗/系統/理論/綜述）

### 🎯 **期刊匹配 (v0.9.1+)**
- **55 本 Q1 期刊檔案**：真實影響因子、接受率、範圍關鍵字
- **加權適配度**：範圍(35%) + 貢獻風格(20%) + 評估風格(20%) + 引用鄰域(15%) + 運營(10%)
- **三層推薦**：目標/備選/安全 + 桌面拒稿風險

### ✍️ **Journal-Aware Writing Style Optimization (v0.10.1)**
- **風格分析**：自動提取目標期刊（如 IEEE TPAMI vs. ACM TOSEM）的偏好措辭與結構，支援 55 本 Q1 期刊
- **8 項量化指標**：Flesch-Kincaid 等級、SMOG 指數、句長、詞長、詞彙多樣性、技術術語密度、被動語態比例、名詞化比例
- **逐章節診斷**：`crane_diagnose_paper` 對每個章節計算偏差分數，識別 critical/major/minor 問題
- **互動式改寫**：`crane_start_rewrite_session` 啟動 accept/reject/modify 工作流，逐條審核改寫建議
- **偏好學習**：`PreferenceLearnerService` 跨工作階段記錄您的決策模式，自動調整未來建議的優先級
- **多域名支援**：AI/ML、Cybersecurity、IoT、MIS 四個域名包，每個域名有不同的指標權重
- **期刊比較**：`crane_compare_sections` 並排比較兩本期刊對同一章節的風格期望差異
- **完整報告**：`crane_export_style_report` 生成 Markdown 格式的風格分析報告

---

### 🔧 **修改規劃 (v0.9.1+)**
- **三層報告**：計分卡(分數 + 閘值 + 準備度) + 證據檢視(維度級別) + 修改待辦清單(優先級)
- **ROI 排序**：影響 × 工作量矩陣
- **修改前後追蹤**：快照評分、重新評估、查看差異

### 🧠 **LeCun 推理框架 (v0.9.3+)**
- **世界模型投稿預測**：因果推理預測接受/修改/拒稿情景
- **5 層策略分析**：文明→領域→方法→課題→操作，檢測層級錯位
- **第一性原則解構**：剝離領域內的假設，識別逆向機會

### 🔐 **權限規則引擎 (v0.9.3+)**
- **三類規則**：`allow`(自動批准) + `soft_deny`(需確認) + `environment`(情境)
- **REPLACE 語義合併**：使用者規則替代預設規則，而非全有全無
- **動態評估**：`evaluate_permission_action` 傳回 allow/deny/ask

---

## 快速開始（5 個命令啟動第一個管道）

```bash
# 1. 安裝 CRANE
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
cd ~/.opencode-crane && uv sync

# 2. 初始化研究專案
crane init research --field="AI/ML" --type="literature-review"

# 3. 搜索與添加文獻
crane search papers --query="Scaling Laws in LLMs" --max=20
crane add reference --paper-id="arxiv:2001.08361"

# 4. 執行評估管道
crane evaluate paper --path="main.tex"

# 5. 生成修改計劃
crane generate revision-report --path="main.tex"
```

---

## 安裝

### 前置需求
- **Python**: 3.10+
- **工具**：[uv](https://astral.sh/uv/install.sh)（快速套件管理器）
- **作業系統**：Linux (Ubuntu 20.04+) 或 macOS

### 快速安裝
```bash
# 克隆並同步
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
cd ~/.opencode-crane && uv sync

# 驗證安裝
uv run pytest tests/ -q
```

---

## 功能對比

| 特性 | CRANE | Zotero | Mendeley | Obsidian |
|------|-------|--------|----------|----------|
| **AI 自主性** | 原生 MCP | 第三方插件 | 有限 | 手動設置 |
| **Q1 評估** | 7 維證據優先 | ✗ | ✗ | ✗ |
| **期刊匹配** | 55 本 Q1 期刊 | ✗ | ✗ | ✗ |
| **寫作風格優化** | Journal-Aware + 互動改寫 | ✗ | ✗ | ✗ |
| **修改規劃** | 三層 + ROI 排序 | ✗ | ✗ | ✗ |
| **PICOS 篩選** | 自動提取 | ✗ | ✗ | ✗ |
| **論文審核** | 章節級邏輯 | ✗ | ✗ | ✗ |
| **多域名支援** | 4 域名（CS, Cybersecurity, IoT, MIS） | ✗ | ✗ | ✗ |
| **開發者友善** | CLI/MCP/YAML | GUI 重 | GUI 重 | 筆記重 |

---

## 實際應用案例

### 1️⃣ 系統文獻綜述
**場景**：博士生需篩選 500 篇「LoRa 安全」論文

```bash
crane run-pipeline \
  --pipeline="literature-review" \
  --topic="LoRa Security" \
  --max-papers=500 \
  --include-picos
```

**結果**：CRANE 搜索 arXiv/OpenAlex、下載 PDF、提取摘要、創建 GitHub 專案板、PICOS 自動篩選

---

### 2️⃣ Q1 投稿準備
**場景**：研究人員評估論文是否準備好投稿 Q1 期刊

```bash
crane evaluate paper --path="main.tex"
crane match journal --path="main.tex"
crane generate-revision-report --path="main.tex"
```

**結果**：
- 7 維評分：方法論 78/100、評估 65/100...
- 期刊推薦：IEEE TPAMI(目標)、TNNLS(備選)、PR(安全)
- 修改清單：添加消融研究(+12 分)、統計顯著性測試(+8 分)

---

### 3️⃣ ACM TOSEM 投稿流程
**場景**：準備投稿 ACM TOSEM

```bash
# 一鍵完整檢查
crane run-submission-check --paper="main.tex" --journal="ACM TOSEM"
```

**結果**：
- 文獻檢查清單（40 項）
- 實驗數據彙總（156 項）
- 論文健康報告（8 項檢查）
- 優先級排序改進計劃（1-3 週內完成）
- 個性化投稿信

---

## 開發指南

### 環境設置
```bash
cd ~/.opencode-crane
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 運行測試
```bash
# 完整測試套件
uv run pytest tests/ -v
# 覆蓋率報告
uv run pytest tests/ --cov=crane --cov-report=term-missing
```

### 專案結構
```
src/crane/
  models/          # 資料模型（含 writing_style_models）
  services/        # 業務邏輯 (25+ 服務，含 writing_style, interactive_rewrite, preference_learner)
  tools/           # MCP 工具註冊 (90+ 工具，含 13 個寫作風格工具)
  config/          # 領域包與配置（AI/ML, Cybersecurity, IoT, MIS）
  providers/       # 學術資料源 (arXiv, OpenAlex)
data/
  journals/        # Q1 期刊檔案 (55 本)
  style_guides/    # 期刊風格指南快取
  rewrite_sessions/ # 互動改寫工作階段
  user_preferences/ # 使用者偏好學習狀態
  review_patterns/ # 評審模式與批評框架
tests/
  services/        # 單元測試 (1500+ 測試)
  integration/     # 集成測試
```

---

## 版本歷史

| 版本 | 發佈日期 | 重點 |
|------|----------|------|
| **v0.10.1** | 2026-04-06 | Journal-Aware Writing Style Toolkit：55 本期刊風格分析、互動式改寫工作流、偏好學習引擎、4 域名支援、13 個新 MCP 工具 |
| **v0.10.0** | 2026-04-06 | ACM TOSEM 投稿完整工具鏈：投稿前檢查、期刊策略、修改追蹤、論文模板、性能基準、使用者評估框架 |
| v0.9.4 | 2026-04-04 | 第 5 階段：紙碼一致性、研究管道基準、信任校準、工具編排 |
| v0.9.3 | 2026-04-04 | LeCun 框架、代理管理、權限規則、傳輸與工作階段 |
| v0.9.2 | 2026-04-03 | 遷移框架、版本管理 |
| v0.9.1 | 2026-04-02 | Q1 評估 v2、期刊匹配、修改規劃 |
| v0.9.0 | 2026-04-01 | 初始版本：文獻綜述、PICOS、引用圖 |

---

## 授權

MIT 授權

## 引用
```bibtex
@article{zhang2025scaling,
  title={Scaling Laws in Scientific Discovery with AI and Robot Scientists},
  author={Zhang, Pengsong and others},
  journal={arXiv preprint arXiv:2503.22444},
  year={2025}
}
```

---

## 補充：完整安裝指南

### 1. 工具鏈
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://bun.sh/install | bash
hash -r
```

### 2. 安裝 CRANE
```bash
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
cd ~/.opencode-crane && uv sync
```

### 3. 設定 OpenCode
```bash
OPENCODE="$HOME/.config/opencode"
cat > "$OPENCODE/opencode.json" << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["oh-my-opencode"],
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["sh", "-c", "cd $HOME/.opencode-crane && uv run crane"],
      "enabled": true
    }
  }
}
EOF
```

---

**立即開始**：執行 `crane init research` 並按照引導式工作流走完整個研究過程！
