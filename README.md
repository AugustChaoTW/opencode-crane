# opencode-crane

**CRANE** — 自主研究助理 MCP Server，專為 [OpenCode](https://github.com/anomalyco/opencode) 設計。

將完整的學術研究工作流程（文獻搜尋 → 提案 → 實驗 → 寫作 → 審閱）整合為一組 MCP 工具，透過 GitHub Issues 追蹤任務，以檔案式管理（YAML + BibTeX）維護引用文獻。

> **CRANE**（鶴）：象徵智慧、耐心與精準。鶴耐心觀察水面，一擊命中——正如研究者深度閱讀文獻後精準提取洞見。

---

## 主要功能

- **章節級論文審查** — 逐章節偵測 6 種常見問題（邏輯錯誤、數據不一致、過度聲張、完整性缺失、AI 寫作痕跡、圖表品質）
- **LaTeX 結構解析** — 自動偵測 `\section{}`、`\subsection{}`、`\appendix`
- **3-LLM 論文驗證** — Auditor/Detector/Editor 三角色 AI 審查流程
- **AI 寫作偵測** — L1 詞彙、L2 段落節奏、L3 學術主體性三層分析
- **Protected Zones** — 驗證通過內容自動保護，防止意外修改
- **期刊推薦** — 自動推薦 Q1/Q2 適合投稿的期刊（OpenAlex + SJR）
- **向量圖產生** — Matplotlib/Seaborn 產生 PDF 格式 publication-quality 圖表
- **多來源論文搜尋** — 支援 arXiv、OpenAlex、Semantic Scholar、Crossref 四大資料庫
- **文獻庫管理** — YAML + BibTeX 雙格式儲存，支援搜尋、篩選、AI 標註
- **元資料標準化** — 自動去重、衝突解決、引用數量聚合
- **引用驗證** — 檢查論文引用一致性，驗證文獻元資料
- **篩選與比較** — 系統性文獻回顧的納入/排除決策，多維度比較矩陣
- **證據溯源** — 所有 AI 產出可追溯至原文來源
- **研究任務追蹤** — 透過 GitHub Issues 管理任務與待辦事項
- **工作區管理** — Stateless 設計，自動從 git context 解析工作區
- **可靠執行** — 自動重試機制，優雅處理網路失敗
- **研究階段管理** — 文獻回顧 → 提案 → 實驗 → 寫作 → 審閱，全程追蹤進度
- **專案初始化** — 一鍵設定研究專案結構（labels、milestones、目錄、Issue Template）
- **OpenCode 原生整合** — MCP Server 架構，AI agent 透過自然語言直接操作

---

## 快速命令卡

> 💡 **快捷參考**：常用自然語言指令對應的 CRANE 工具

<table>
<tr><th>你的需求</th><th>自然語言</th><th>對應工具</th></tr>

<tr><td>🚀 初始化專案</td><td><code>幫我初始化這個 repo 為研究專案</code></td><td><code>init_research</code></td></tr>

<tr><td>🔍 搜尋論文</td><td><code>搜尋關於 transformer 的論文</code></td><td><code>search_papers</code></td></tr>

<tr><td>📥 加入文獻</td><td><code>把這篇論文加入文獻庫</code></td><td><code>add_reference</code></td></tr>

<tr><td>📄 下載 PDF</td><td><code>下載論文 2301.00001</code></td><td><code>download_paper</code></td></tr>

<tr><td>📖 閱讀論文</td><td><code>幫我閱讀這篇論文並摘要</code></td><td><code>read_paper</code></td></tr>

<tr><td>✅ 檢查引用</td><td><code>檢查論文中的引用是否都有文獻</code></td><td><code>check_citations</code></td></tr>

<tr><td>🔎 驗證文獻</td><td><code>驗證 vaswani2017-attention 的 DOI</code></td><td><code>verify_reference</code></td></tr>

<tr><td>📋 建立任務</td><td><code>建立一個文獻回顧任務</code></td><td><code>create_task</code></td></tr>

<tr><td>📝 建立待辦</td><td><code>建立待辦：review 第三章</code></td><td><code>create_task(type="todo")</code></td></tr>

<tr><td>📊 查看進度</td><td><code>目前的任務進度如何？</code></td><td><code>get_milestone_progress</code></td></tr>

<tr><td>🏠 工作區狀態</td><td><code>顯示工作區概覽</code></td><td><code>workspace_status</code></td></tr>

<tr><td>🔄 執行工作流</td><td><code>幫我做文獻回顧</code></td><td><code>run_pipeline</code></td></tr>

<tr><td>📊 篩選文獻</td><td><code>把這篇論文標記為納入</code></td><td><code>screen_reference</code></td></tr>

<tr><td>🔍 比較論文</td><td><code>比較這三篇論文的差異</code></td><td><code>compare_papers</code></td></tr>

<tr><td>🔬 驗證論文</td><td><code>幫我驗證這篇論文的品質</code></td><td><code>verify_paper</code></td></tr>

<tr><td>🎯 推薦期刊</td><td><code>推薦適合投稿的期刊</code></td><td><code>recommend_journals</code></td></tr>

<tr><td>📊 產生圖表</td><td><code>產生一個比較圖表</code></td><td><code>generate_figure</code></td></tr>

<tr><td>📝 審查章節</td><td><code>幫我審查這篇論文的各個章節</code></td><td><code>review_paper_sections</code></td></tr>

<tr><td>🔍 解析結構</td><td><code>解析這篇論文的章節結構</code></td><td><code>parse_paper_structure</code></td></tr>

</table>

### Label 對照表

| 類別 | Labels | 說明 |
|------|--------|------|
| 🔖 CRANE 標記 | `crane` | 所有 CRANE 管理的 issues |
| 📌 類型 | `kind:task` / `kind:todo` | 任務 / 待辦 |
| 🎯 階段 | `phase:literature-review`<br>`phase:proposal`<br>`phase:experiment`<br>`phase:writing`<br>`phase:review` | 研究階段 |
| 🏷️ 任務類型 | `type:search` / `type:read`<br>`type:analysis` / `type:code` / `type:write` | 任務性質 |
| ⚡ 優先級 | `priority:high`<br>`priority:medium`<br>`priority:low` | 優先順序 |

### 典型工作流程

#### 文獻回顧流程

```
1️⃣ 初始化        → init_research
      ↓
2️⃣ 文獻搜尋      → search_papers → add_reference → download_paper
      ↓
3️⃣ 閱讀標註      → read_paper → annotate_reference
      ↓
4️⃣ 篩選比較      → screen_reference → compare_papers
      ↓
5️⃣ 任務追蹤      → create_task → report_progress → close_task
      ↓
6️⃣ 引用驗證      → check_citations → verify_reference
      ↓
7️⃣ 進度查看      → workspace_status → get_milestone_progress
```

#### 3-LLM 論文驗證流程

```
1️⃣ 推薦期刊      → recommend_journals
      ↓
2️⃣ AUDIT        → LLM-A: 圖表資料追溯 + 引用驗證
      ↓
3️⃣ DETECTION    → LLM-B: L1/L2/L3 AI 寫作偵測
      ↓
4️⃣ EDITING      → LLM-C: 約束式重寫
      ↓
5️⃣ RE-VERIFY    → LLM-A: 驗證修改（FAIL → 回傳 Step 4）
      ↓
6️⃣ 產生圖表     → generate_figure / generate_comparison
      ↓
7️⃣ 報告         → PAPER_HEALTH_REPORT.md
```

#### 章節級論文審查流程

```
1️⃣ 解析結構     → parse_paper_structure
      ↓
2️⃣ 逐章節審查   → review_paper_sections
      ├─ 邏輯錯誤 (logic)
      ├─ 數據一致性 (data)
      ├─ 聲稱範圍 (framing)
      ├─ 完整性 (completeness)
      ├─ AI 寫作痕跡 (writing)
      └─ 圖表品質 (figures)
      ↓
3️⃣ 產生報告     → section_review_report.yaml
      ↓
4️⃣ 修正問題     → 根據建議逐一修正
      ↓
5️⃣ 重新驗證     → 重新執行審查
```

### 章節審查類型

| 類型 | 偵測項目 | 常見問題範例 |
|------|----------|-------------|
| `logic` | Python 邏輯錯誤、算法正確性 | `if "good" or "positive" in text` |
| `data` | 百分比、成本、延遲一致性 | 62.5% vs 87.5% 矛盾 |
| `framing` | 過度聲張、術語濫用 | "neuro-symbolic expert system" |
| `completeness` | 基線缺失、限制未討論 | 缺 constrained decoding baseline |
| `writing` | AI 寫作痕跡、模糊量詞 | "It is worth noting that" |
| `figures` | 圖表複雜度、圖說完整性 | Figure 1 過度複雜 |

### 3-LLM 角色定義

| 角色 | 認知模式 | 職責 |
|------|----------|------|
| **LLM-A (Auditor)** | 精確、保守、二元判斷 | 資料追溯、引用驗證、重新驗證 |
| **LLM-B (Detector)** | 模式敏感、語言學分析 | L1 詞彙、L2 段落、L3 主體性偵測 |
| **LLM-C (Editor)** | 創意、領域專家 | 約束式重寫、保留 Protected Zones |

---

## 快速安裝

### 一鍵安裝（推薦）

```bash
curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash
```

安裝完成後，在你的研究專案中執行：

```bash
cd ~/your-research-project
bash ~/.opencode-crane/scripts/setup-project.sh
```

完成。啟動 OpenCode 即可使用。

---

<!-- OPENCODE-INSTALL-GUIDE-BEGIN -->
## 安裝指南（OpenCode 可讀取執行）

> **給 AI Agent 的說明**：以下步驟可直接依序執行。每個步驟都是獨立的 shell 指令，
> 附帶驗證方式。如果使用者說「幫我安裝 crane」，請按照這個流程操作。

### 系統需求

支援作業系統：Ubuntu 20.04+、Rocky Linux 8+、RHEL 8+、Fedora 36+

### 一鍵安裝（推薦）

```bash
curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash
```

完成後，跳到 **[專案設定](#專案設定)**。

### 手動安裝

從頭到尾複製貼上即可。每一行可獨立執行。

#### 安裝工具鏈

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://bun.sh/install | bash
hash -r
```

#### 安裝 CRANE

```bash
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
cd ~/.opencode-crane && uv sync
```

#### 安裝 Plugin

```bash
OPENCODE="$HOME/.config/opencode"

cat > "$OPENCODE/package.json" << 'EOF'
{
  "dependencies": {
    "@opencode-ai/plugin": "^1.3.2",
    "oh-my-opencode": "^3.12.3",
    "opencode-claude-auth": "^1.3.1"
  }
}
EOF
cd "$OPENCODE" && bun install

mkdir -p "$OPENCODE/plugins/claude-max-headers"
curl -fsSL https://raw.githubusercontent.com/rynfar/opencode-claude-max-proxy/main/src/plugin/claude-max-headers.ts \
  -o "$OPENCODE/plugins/claude-max-headers/claude-max-headers.ts"

git clone --depth 1 https://github.com/AugustChaoTW/aug-money.git /tmp/aug-money
cd /tmp/aug-money/opencode-memory-system && bun install && bun run build
mkdir -p "$OPENCODE/plugins/memory-system"
cp dist/index.js dist/sql-wasm.wasm package.json "$OPENCODE/plugins/memory-system/"
rm -rf /tmp/aug-money
```

#### 寫入配置

```bash
OPENCODE="$HOME/.config/opencode"

cat > "$OPENCODE/opencode.json" << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "oh-my-opencode",
    "opencode-claude-auth",
    "./plugins/claude-max-headers/claude-max-headers.ts",
    "./plugins/memory-system"
  ],
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["sh", "-c", "cd $HOME/.opencode-crane && uv run crane"],
      "enabled": true
    }
  }
}
EOF

cat > "$OPENCODE/oh-my-opencode.json" << 'EOF'
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json",
  "google_auth": false,
  "agents": {}
}
EOF
```

#### 安裝 SKILL.md

```bash
mkdir -p "$HOME/.config/opencode/skills/opencode-crane"
cp ~/.opencode-crane/SKILL.md "$HOME/.config/opencode/skills/opencode-crane/SKILL.md"
```

---

### 專案設定

在你的研究專案根目錄執行，完成 MCP + gitignore 設定：

```bash
# 方法 A：使用腳本（推薦）
bash ~/.opencode-crane/scripts/setup-project.sh
```

```bash
# 方法 B：手動
cd ~/your-research-project
mkdir -p .opencode
cat > .opencode/opencode.json << 'EOF'
{
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["sh", "-c", "cd $HOME/.opencode-crane && uv run crane"],
      "enabled": true
    }
  }
}
EOF
mkdir -p .opencode/skills/opencode-crane
cp ~/.opencode-crane/SKILL.md .opencode/skills/opencode-crane/SKILL.md
grep -q "references/pdfs/" .gitignore 2>/dev/null || echo "references/pdfs/" >> .gitignore
```

#### 驗證

```bash
# CRANE 本體
cd ~/.opencode-crane && uv run python -c "from crane.server import mcp; print(f'OK: {len(mcp._tool_manager._tools)} tools registered')"

# Plugin 狀態
echo "oh-my-opencode:      $([ -d ~/.config/opencode/node_modules/oh-my-opencode ] && echo '✓' || echo '✗')"
echo "opencode-claude-auth: $([ -d ~/.config/opencode/node_modules/opencode-claude-auth ] && echo '✓' || echo '✗')"
echo "claude-max-headers:   $([ -f ~/.config/opencode/plugins/claude-max-headers/claude-max-headers.ts ] && echo '✓' || echo '✗')"
echo "memory-system:        $([ -f ~/.config/opencode/plugins/memory-system/index.js ] && echo '✓' || echo '✗')"
```

預期：`OK: N tools registered` + 全部 ✓

啟動 OpenCode 輸入 `幫我初始化這個 repo 為研究專案` 驗證完整功能。

<!-- OPENCODE-INSTALL-GUIDE-END -->

---

## 更新

```bash
cd ~/.opencode-crane && git pull && uv sync
cd ~/.config/opencode && bun install
```

## 解除安裝

```bash
rm -rf ~/.opencode-crane
rm -rf ~/.config/opencode/plugins/memory-system
rm -rf ~/.config/opencode/plugins/claude-max-headers
rm -f ~/.config/opencode/skills/opencode-crane/SKILL.md
rm -f ~/.config/opencode/oh-my-opencode.json
# 清理 npm plugins: cd ~/.config/opencode && bun install
```

---

## 功能總覽

### 23 個 MCP Tools，分 7 大類

#### 專案管理（2 tools）
| Tool | 說明 |
|------|------|
| `init_research` | 初始化 GitHub repo 為研究專案：建立 labels、milestones、`references/` 目錄、Issue Template |
| `get_project_info` | 取得專案資訊：repo 名稱、branch、milestone 進度、文獻數量 |

#### 論文搜尋（3 tools）
| Tool | 說明 |
|------|------|
| `search_papers` | 搜尋 arXiv 學術論文，回傳標題 / 作者 / 摘要 / DOI / PDF URL |
| `download_paper` | 下載論文 PDF 到 `references/pdfs/` |
| `read_paper` | 讀取 PDF 並抽取全文純文字（若不存在會自動下載） |

#### 文獻管理（6 tools）
| Tool | 說明 |
|------|------|
| `add_reference` | 新增文獻：寫入 `references/papers/{key}.yaml` + 追加到 `bibliography.bib` |
| `list_references` | 列出所有文獻，支援 keyword / tag 篩選 |
| `get_reference` | 取得單篇文獻完整詳情（含 AI 標註） |
| `search_references` | 全文搜尋文獻的 title / authors / abstract / keywords |
| `remove_reference` | 刪除文獻（YAML + BibTeX 條目 + 可選刪 PDF） |
| `annotate_reference` | 為文獻新增 AI 標註：摘要、關鍵貢獻、方法論、相關 Issue |

#### 引用驗證（3 tools）
| Tool | 說明 |
|------|------|
| `check_citations` | 檢查論文中所有 `\cite{key}` 是否存在於文獻庫 |
| `verify_reference` | 驗證文獻元資料（DOI、年份、標題）是否符合預期 |
| `check_all_references` | 檢查所有文獻的元資料完整性（必填欄位） |

#### 任務管理（7 tools）
| Tool | 說明 | 底層 |
|------|------|------|
| `create_task` | 建立研究任務或待辦事項（GitHub Issue），自動加 labels | `gh issue create` |
| `list_tasks` | 列出任務/待辦，按階段 / 狀態 / 類型篩選 | `gh issue list` |
| `view_task` | 查看單個任務內容與留言歷史 | `gh issue view` |
| `update_task` | 更新任務標籤、milestone、指派人 | `gh issue edit` |
| `report_progress` | 在任務上留言回報進度 | `gh issue comment` |
| `close_task` | 完成任務 | `gh issue close` |
| `get_milestone_progress` | 查看各研究階段的進度統計 | `gh api` |

#### 工作區（1 tool）
| Tool | 說明 |
|------|------|
| `workspace_status` | 查詢工作區概覽：repo、文獻統計、任務/待辦、milestone 進度 |

#### 工作流程（1 tool）
| Tool | 說明 |
|------|------|
| `run_pipeline` | 執行預定義的多步驟工作流程（`literature-review` / `full-setup`），支援 checkpoints、skip_steps、dry_run |

---

## 使用方式

安裝完成後，在 OpenCode 中直接用自然語言對話：

### 初始化

```
> 幫我初始化這個 repo 為研究專案
```

### 文獻回顧

```
> 搜尋關於 transformer attention mechanism 的論文
> 把前 3 篇加入文獻庫
> 下載第一篇並幫我摘要重點
```

### 引用驗證

```
> 檢查我的論文 manuscript.tex 中的引用是否都有對應文獻
> 驗證 vaswani2017-attention 這篇論文的 DOI 是否正確
> 列出所有文獻中缺少作者資訊的項目
```

### 任務與待辦管理

```
> 建立一個文獻回顧任務：閱讀 5 篇 attention 相關論文
> 建立待辦事項：review 第三章初稿
> 目前的任務進度如何？
> 列出所有待辦事項
> 標記任務 #1 為已完成
```

### 工作區狀態

```
> 顯示工作區概覽
> 這個專案目前有多少文獻？任務進度如何？
```

---

## 研究工作流程

```
Phase 1: 初始化
  init_research → 建立 labels / milestones / references 目錄

Phase 2: 文獻回顧
  search_papers → add_reference → download_paper → read_paper → annotate_reference
  create_task(phase="literature-review") → report_progress → close_task

Phase 3: 研究提案
  list_references → create_task(phase="proposal")

Phase 4: 實驗
  create_task(phase="experiment") → report_progress

Phase 5: 寫作
  get_reference → check_citations → create_task(phase="writing")

Phase 6: 審閱
  create_task(phase="review") → get_milestone_progress
```

---

## 架構設計

### 服務層（Service Layer）

CRANE 採用服務層與工具層分離的架構，確保程式碼重用性和可測試性：

```
src/crane/
├── workspace.py               # 工作區解析模組
│   ├── WorkspaceContext       # 不可變工作區上下文（owner/repo、路徑）
│   └── resolve_workspace()    # 從 git context 自動解析工作區
│
├── services/                  # 業務邏輯層
│   ├── paper_service.py       # arXiv 搜尋 / 下載 / 閱讀
│   ├── reference_service.py   # YAML + BibTeX CRUD
│   ├── task_service.py        # GitHub Issues 管理（含 todo 支援）
│   └── citation_service.py    # 引用驗證邏輯
│
├── tools/                     # MCP 工具層（薄封裝）
│   ├── papers.py              # → PaperService
│   ├── references.py          # → ReferenceService
│   ├── tasks.py               # → TaskService
│   ├── citations.py           # → CitationService
│   ├── pipeline.py            # 工作流程編排 → 所有 services
│   ├── project.py             # 專案初始化
│   └── workspace.py           # 工作區狀態查詢
│
└── server.py                  # MCP Server 入口
```

### 工作區系統（Workspace System）

CRANE 使用 Stateless 設計，每次呼叫自動從 git context 解析工作區：

- **工作區識別**：使用 `owner/repo`（GitHub repo）作為標準 ID
- **自動偵測**：從 `cwd` 自動解析 git repo
- **狀態重建**：混合讀取——References（檔案式）+ Issues（GitHub API）

```
Workspace 狀態來源：
├── references/           # 檔案式儲存
│   ├── papers/*.yaml     # 文獻元資料
│   ├── pdfs/*.pdf        # PDF 檔案
│   └── bibliography.bib  # BibTeX 彙總
│
└── GitHub Issues         # 任務與待辦
    ├── kind:task         # 一般任務
    ├── kind:todo         # Runtime 待辦
    ├── phase:*           # 研究階段
    └── priority:*        # 優先級
```

### Label 系統

| Label | 用途 | 範例 |
|-------|------|------|
| `crane` | CRANE 管理的 issues 篩選標記 | 所有 CRANE 建立的 issues |
| `kind:task` | 一般任務 | 建立的正式任務 |
| `kind:todo` | Runtime 待辦事項 | 執行期間產生的待辦 |
| `phase:*` | 研究階段 | `phase:literature-review` |
| `type:*` | 任務類型 | `type:search`、`type:read` |
| `priority:*` | 優先級 | `priority:high` |

---

## 資料管理

### 文獻儲存結構

```
{project-root}/
└── references/
    ├── bibliography.bib            # BibTeX 彙總（可直接用於 LaTeX）
    ├── papers/                     # 每篇文獻一個 YAML
    │   ├── vaswani2017-attention.yaml
    │   └── ...
    └── pdfs/                       # PDF 檔案（.gitignore）
        └── ...
```

### 文獻 YAML 格式

```yaml
key: vaswani2017-attention
title: "Attention Is All You Need"
authors:
  - Vaswani
  - Shazeer
  - Parmar
year: 2017
doi: "10.48550/arXiv.1706.03762"
url: "https://arxiv.org/abs/1706.03762"
pdf_url: "https://arxiv.org/pdf/1706.03762.pdf"
venue: "NeurIPS"
source: arxiv
paper_type: conference
categories:
  - cs.CL
keywords:
  - transformer
  - attention

# AI 產生的標註
ai_annotations:
  summary: "提出 Transformer 架構，以 self-attention 取代 RNN..."
  key_contributions:
    - "首次提出純 attention 架構"
    - "多頭注意力機制"
  methodology: "Encoder-decoder with self-attention"
  relevance_notes: "本研究的核心基礎論文"
  tags:
    - foundation
    - architecture
  related_issues:
    - 5
    - 12
  added_date: "2025-03-15"
```

### GitHub Issues 結構

CRANE 使用 GitHub Issues 追蹤所有任務與待辦：

```
Issue: "[LIT] 閱讀 attention 相關論文"
Labels: crane, kind:task, phase:literature-review, type:read, priority:medium
Milestone: Phase 2: Literature Review
Assignee: @me

Comments:
  - 2025-03-15: "已閱讀 3/5 篇論文"
  - 2025-03-16: "完成所有閱讀，開始撰寫摘要"
```

---

## 開發

### 環境設定

```bash
cd ~/.opencode-crane
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### 執行測試

```bash
# 完整測試套件
.venv/bin/python -m pytest tests/ -v

# 特定測試類別
.venv/bin/python -m pytest tests/services/ -v    # 服務層測試
.venv/bin/python -m pytest tests/tools/ -v       # 工具層測試
.venv/bin/python -m pytest tests/integration/ -v # 整合測試

# 覆蓋率報告
.venv/bin/python -m pytest tests/ --cov=crane --cov-report=term-missing
```

### 專案結構

```
opencode-crane/
├── pyproject.toml               # 專案設定與依賴
├── README.md                    # 本文件
├── SKILL.md                     # OpenCode Skill 定義（AI agent 指引）
├── OPENCODE_GH_FEAT_DESIGN.md   # 完整設計規格書
│
├── scripts/
│   ├── install.sh               # 一鍵安裝腳本
│   └── setup-project.sh         # 專案設定腳本
│
├── src/crane/                   # 主套件
│   ├── server.py                # MCP Server 入口
│   ├── workspace.py             # 工作區解析模組
│   ├── models/
│   │   └── paper.py             # Paper + AiAnnotations 資料模型
│   ├── services/                # 業務邏輯層
│   │   ├── paper_service.py
│   │   ├── reference_service.py
│   │   ├── task_service.py
│   │   └── citation_service.py
│   ├── tools/                   # MCP 工具層
│   │   ├── papers.py
│   │   ├── references.py
│   │   ├── tasks.py
│   │   ├── citations.py
│   │   ├── pipeline.py
│   │   ├── project.py
│   │   └── workspace.py
│   └── utils/                   # 工具函數
│       ├── gh.py                # GitHub CLI 封裝
│       ├── git.py               # Git 操作
│       ├── bibtex.py            # BibTeX 讀寫
│       └── yaml_io.py           # YAML 讀寫
│
├── tests/                       # 測試套件（265 tests）
│   ├── services/                # 服務層測試
│   ├── tools/                   # 工具層測試
│   ├── integration/             # 整合測試
│   ├── models/                  # 模型測試
│   └── utils/                   # 工具函數測試
│
└── _archive/                    # 舊版程式碼封存（gscientist）
```

---

## 設計文件

完整規格請參閱 [`OPENCODE_GH_FEAT_DESIGN.md`](./OPENCODE_GH_FEAT_DESIGN.md)

---

## 授權

MIT License

## 引用

```bibtex
@article{zhang2025scaling,
  title={Scaling Laws in Scientific Discovery with AI and Robot Scientists},
  author={Zhang, Pengsong and others},
  journal={arXiv preprint arXiv:2503.22444},
  year={2025}
}
```
