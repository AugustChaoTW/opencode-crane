# opencode-crane: Feature Design

> CRANE — Autonomous Research Assistant MCP Server for OpenCode + `gh` CLI

## 1. 架構總覽

### 1.1 設計決策

| 決策項 | 選擇 | 理由 |
|--------|------|------|
| **專案名稱** | opencode-crane | 代號 CRANE（鶴），象徵智慧、耐心、精準 |
| **Plugin 形式** | Python MCP Server | 保留現有 Python 程式碼（arXiv、PyPDF2）、`subprocess` 可呼叫 `gh` CLI、OpenCode 原生支援 MCP |
| **專案管理** | 工作目錄 = 專案，GitHub Repo = 身份 | 不需獨立 workspace，git repo 即研究專案 |
| **任務管理** | GitHub Issues via `gh` CLI | 原生 labels/milestones/comments、團隊協作、版本追蹤 |
| **文獻管理** | `references/` 目錄（BibTeX + YAML） | git 友善、AI 可讀寫、學術工具互通 |
| **AI 指引** | SKILL.md | 告知 AI agent 何時/如何使用工具 |

### 1.2 系統架構圖

```
使用者
  │
  ▼
OpenCode CLI (AI Agent)
  │
  ├── 載入 SKILL.md（研究助理指引）
  │
  ├── 連接 MCP Server（auto-research-mcp）
  │     │
  │     ├── 論文搜尋工具 ──→ arXiv API / Google Scholar
  │     ├── 文獻管理工具 ──→ references/ 目錄（YAML + BibTeX）
  │     ├── 任務管理工具 ──→ gh issue create/list/edit/close
  │     ├── 專案資訊工具 ──→ git remote / repo metadata
  │     └── PDF 處理工具 ──→ PyPDF2 / 本地檔案系統
  │
  └── 原生 OpenCode 工具（檔案讀寫、Shell、瀏覽器等）
```

### 1.3 砍掉的元件

| 原元件 | 原因 |
|--------|------|
| FastAPI 後端（12 端點） | MCP Server 取代 |
| Web UI（HTML/JS/CSS） | OpenCode 是 CLI，不需 Web 前端 |
| 雙 SQLite DB（papers.db + references.db） | 檔案式管理（YAML + BibTeX）取代 |
| ProjectManager + YAML 專案設定 | git repo 即專案 |
| ProjectService / ReferencesService / AgentService | MCP Tool 直接暴露功能 |
| `sciagents` 依賴（ChatAgent, LlmModel） | OpenCode 本身就是 AI Agent |

---

## 2. 現有功能盤點（按研究階段）

### 2.1 功能對照表

| 研究階段 | 現有功能 | 原實作狀態 | 新設計對應 |
|----------|---------|-----------|-----------|
| **文獻回顧** | arXiv 關鍵字搜尋 | ✅ 完成 | `search_papers` tool |
| | PDF 下載到本地 | ✅ 完成 | `download_paper` tool |
| | PDF 全文文字抽取 | ✅ 完成 | `read_paper` tool |
| | Paper 資料模型（22+ 欄位） | ✅ 完成 | YAML schema 重新設計 |
| | 論文寫入全域 DB | ✅ 完成 | `add_reference` tool（寫檔） |
| | 論文全文搜尋 | ✅ 完成 | `search_references` tool（grep YAML） |
| | 專案-論文關聯（DOI 外鍵） | ✅ 完成 | 不需要（單 repo = 單專案） |
| | Google Scholar 搜尋 | ❌ 空 stub | 未來擴充 |
| **提案** | Proposal/ 資料夾建立 | ✅ 僅目錄 | 不需（使用者自行組織目錄） |
| | 提案撰寫工具 | ❌ 無 | 由 AI Agent 直接處理 |
| **實驗** | Experiment/ 資料夾建立 | ✅ 僅目錄 | 不需 |
| | 實驗執行工具 | ❌ 無 | 由 AI Agent + Shell 處理 |
| **寫作** | Manuscript/ 資料夾建立 | ✅ 僅目錄 | 不需 |
| | 編輯器 UI | ⚠️ Stub | OpenCode 原生檔案編輯 |
| **審閱** | — | ❌ 無 | 由 AI Agent 直接處理 |
| **跨領域** | GSAgent 通用對話 | ✅ 完成 | OpenCode 本身即 Agent |
| | SciSearchAgent 論文搜尋 | ✅ 完成 | `search_papers` tool |
| | AgentFactory 動態發現 | ✅ 完成 | 不需（MCP 直接註冊） |
| | FunctionTool 工具註冊 | ✅ 完成 | `@mcp.tool()` 取代 |
| | 專案 CRUD | ✅ 完成 | `get_project_info` + `init_research` |
| | 串流回應（SSE/WebSocket） | ✅ 完成 | MCP `ctx.report_progress()` |
| | 任務規劃（Planner） | ⚠️ Stub | `create_task` / `list_tasks` 等 |

---

## 3. MCP Tool 完整設計

### 3.1 Tool 總覽

共 **18 個 MCP Tools**，分 4 大類：

```
opencode-crane (src/crane/)
├── tools/
│   ├── project/        # 專案管理（2 tools）
│   │   ├── init_research
│   │   └── get_project_info
│   ├── papers/         # 論文搜尋（3 tools）
│   │   ├── search_papers
│   │   ├── download_paper
│   │   └── read_paper
│   ├── references/     # 文獻管理（6 tools）
│   │   ├── add_reference
│   │   ├── list_references
│   │   ├── get_reference
│   │   ├── search_references
│   │   ├── remove_reference
│   │   └── annotate_reference
│   └── tasks/          # 任務管理（7 tools）
│       ├── create_task
│       ├── list_tasks
│       ├── view_task
│       ├── update_task
│       ├── report_progress
│       ├── close_task
│       └── get_milestone_progress
```

### 3.2 專案管理 Tools

#### `init_research`

初始化當前 repo 為研究專案，建立所需的 GitHub labels、milestones、references 目錄結構。

```python
@mcp.tool()
def init_research(
    phases: list[str] = ["literature-review", "proposal", "experiment", "writing", "review"]
) -> str:
    """
    初始化當前 GitHub repo 為研究專案。
    建立 phase labels、type labels、priority labels、milestones、
    references/ 目錄結構、.github/ISSUE_TEMPLATE/research-task.yml。
    """
```

**執行動作**：
1. `gh label create "phase:{phase}" --color {color} --force`（每個 phase）
2. `gh label create "type:{type}" --force`（search/read/analysis/code/write）
3. `gh label create "priority:{level}" --force`（high/medium/low）
4. `gh api -X POST repos/{owner}/{repo}/milestones -f title="Phase N: {phase}"`
5. `mkdir -p references/papers references/pdfs`
6. 建立 `references/bibliography.bib`（空檔）
7. 建立 `.github/ISSUE_TEMPLATE/research-task.yml`

**Labels 色碼定義**：

| Label | 色碼 | 用途 |
|-------|------|------|
| `phase:literature-review` | `#0E8A16` | 文獻回顧階段 |
| `phase:proposal` | `#1D76DB` | 研究提案階段 |
| `phase:experiment` | `#D93F0B` | 實驗階段 |
| `phase:writing` | `#FBCA04` | 寫作階段 |
| `phase:review` | `#6F42C1` | 審閱階段 |
| `type:search` | `#C5DEF5` | 搜尋類任務 |
| `type:read` | `#BFD4F2` | 閱讀類任務 |
| `type:analysis` | `#D4C5F9` | 分析類任務 |
| `type:code` | `#F9D0C4` | 程式碼類任務 |
| `type:write` | `#FEF2C0` | 撰寫類任務 |
| `priority:high` | `#D93F0B` | 高優先 |
| `priority:medium` | `#FBCA04` | 中優先 |
| `priority:low` | `#0E8A16` | 低優先 |

#### `get_project_info`

```python
@mcp.tool()
def get_project_info() -> dict:
    """
    取得當前研究專案資訊：repo 名稱、remote URL、
    當前 branch、最近 commit、milestone 進度統計。
    """
```

**執行動作**：
1. `git remote get-url origin` → repo URL
2. `git rev-parse --abbrev-ref HEAD` → 當前 branch
3. `git log -1 --format='%H %s'` → 最近 commit
4. `gh api repos/{owner}/{repo}/milestones --jq ...` → milestone 統計
5. `ls references/papers/*.yaml | wc -l` → 文獻數量

**輸出範例**：
```json
{
  "repo": "augchao/auto-research",
  "branch": "main",
  "last_commit": "827b435 add search_agent",
  "references_count": 12,
  "milestones": [
    {"name": "Phase 1: Literature Review", "open": 3, "closed": 7, "progress": "70%"},
    {"name": "Phase 2: Proposal", "open": 5, "closed": 0, "progress": "0%"}
  ]
}
```

### 3.3 論文搜尋 Tools

#### `search_papers`

```python
@mcp.tool()
def search_papers(
    query: str,
    max_results: int = 10,
    source: str = "arxiv"
) -> list[dict]:
    """
    搜尋學術論文。回傳論文清單，每篇包含 title、authors、abstract、
    doi、url、pdf_url、published_date、categories。
    支援 source: arxiv（未來可擴充 google_scholar、semantic_scholar）。
    """
```

**底層實作**：保留 `ArxivSearcher.search()` 核心邏輯（`arxiv.py:20-79`）
**輸出**：`List[dict]` — 每個 dict 對應一篇論文的基本元資料

#### `download_paper`

```python
@mcp.tool()
def download_paper(
    paper_id: str,
    save_dir: str = "references/pdfs"
) -> str:
    """
    下載論文 PDF 到 references/pdfs/ 目錄。
    回傳本地檔案路徑。
    """
```

**底層實作**：保留 `ArxivSearcher.download_pdf()` 核心邏輯（`arxiv.py:81-101`）

#### `read_paper`

```python
@mcp.tool()
def read_paper(
    paper_id: str,
    save_dir: str = "references/pdfs"
) -> str:
    """
    讀取論文 PDF 並抽取全文文字。
    若 PDF 不存在會先自動下載。
    回傳全文純文字內容。
    """
```

**底層實作**：保留 `ArxivSearcher.read_paper()` 核心邏輯（`arxiv.py:103-130`）

### 3.4 文獻管理 Tools

#### `add_reference`

```python
@mcp.tool()
def add_reference(
    key: str,
    title: str,
    authors: list[str],
    year: int,
    doi: str = "",
    venue: str = "",
    url: str = "",
    pdf_url: str = "",
    abstract: str = "",
    source: str = "manual",
    paper_type: str = "unknown",
    categories: list[str] = [],
    keywords: list[str] = []
) -> str:
    """
    新增一筆文獻到 references/。
    同時寫入 references/papers/{key}.yaml 和追加到 references/bibliography.bib。
    """
```

**執行動作**：
1. 建立 `references/papers/{key}.yaml`（完整 YAML 結構）
2. 追加 BibTeX 條目到 `references/bibliography.bib`
3. 回傳確認訊息

#### `list_references`

```python
@mcp.tool()
def list_references(
    filter_keyword: str = "",
    filter_tag: str = "",
    limit: int = 50
) -> list[dict]:
    """
    列出 references/papers/ 中的所有文獻。
    支援按 keyword 和 tag 篩選。
    回傳摘要清單（key、title、authors、year、venue）。
    """
```

#### `get_reference`

```python
@mcp.tool()
def get_reference(key: str) -> dict:
    """
    取得單篇文獻的完整資訊（含 ai_annotations）。
    從 references/papers/{key}.yaml 讀取。
    """
```

#### `search_references`

```python
@mcp.tool()
def search_references(query: str) -> list[dict]:
    """
    全文搜尋 references/papers/*.yaml 的 title、authors、abstract、keywords。
    回傳匹配結果。
    """
```

#### `remove_reference`

```python
@mcp.tool()
def remove_reference(key: str, delete_pdf: bool = False) -> str:
    """
    刪除一筆文獻。移除 YAML 檔、從 bibliography.bib 移除條目、
    可選刪除 PDF。
    """
```

#### `annotate_reference`

```python
@mcp.tool()
def annotate_reference(
    key: str,
    summary: str = "",
    key_contributions: list[str] = [],
    methodology: str = "",
    relevance_notes: str = "",
    tags: list[str] = [],
    related_issues: list[int] = []
) -> str:
    """
    為文獻新增或更新 AI 標註（ai_annotations 區塊）。
    寫入 references/papers/{key}.yaml 的 ai_annotations 欄位。
    """
```

### 3.5 任務管理 Tools

#### `create_task`

```python
@mcp.tool()
def create_task(
    title: str,
    body: str = "",
    phase: str = "",
    task_type: str = "",
    priority: str = "",
    milestone: str = "",
    assignee: str = "@me"
) -> dict:
    """
    建立研究任務（GitHub Issue）。
    自動加上 phase/type/priority labels。
    """
```

**執行動作**：
```bash
gh issue create \
  --title "{title}" \
  --body "{body}" \
  --label "phase:{phase},type:{task_type},priority:{priority}" \
  --milestone "{milestone}" \
  --assignee "{assignee}" \
  --json number,url
```

**輸出**：
```json
{"number": 42, "url": "https://github.com/owner/repo/issues/42"}
```

#### `list_tasks`

```python
@mcp.tool()
def list_tasks(
    phase: str = "",
    state: str = "open",
    task_type: str = "",
    milestone: str = "",
    limit: int = 30
) -> list[dict]:
    """
    列出研究任務。支援按 phase、state、type、milestone 篩選。
    """
```

**執行動作**：
```bash
gh issue list \
  --label "phase:{phase}" \
  --state {state} \
  --milestone "{milestone}" \
  --json number,title,labels,state,assignees,milestone,createdAt,updatedAt \
  --limit {limit}
```

#### `view_task`

```python
@mcp.tool()
def view_task(issue_number: int) -> dict:
    """
    查看單個任務的完整內容，包含留言歷史。
    """
```

**執行動作**：
```bash
gh issue view {issue_number} --json number,title,body,state,labels,milestone,assignees,comments,createdAt,updatedAt
```

#### `update_task`

```python
@mcp.tool()
def update_task(
    issue_number: int,
    title: str = "",
    add_labels: list[str] = [],
    remove_labels: list[str] = [],
    milestone: str = "",
    assignee: str = ""
) -> str:
    """
    更新任務的標題、標籤、milestone、指派人。
    """
```

**執行動作**：
```bash
gh issue edit {issue_number} \
  --title "{title}" \
  --add-label "{label1},{label2}" \
  --remove-label "{label3}" \
  --milestone "{milestone}"
```

#### `report_progress`

```python
@mcp.tool()
def report_progress(issue_number: int, comment: str) -> str:
    """
    在任務上留言回報進度。用於記錄研究過程中的發現、決策、結果。
    """
```

**執行動作**：
```bash
gh issue comment {issue_number} --body "{comment}"
```

#### `close_task`

```python
@mcp.tool()
def close_task(
    issue_number: int,
    reason: str = "completed",
    comment: str = ""
) -> str:
    """
    完成任務。reason 可為 completed 或 not_planned。
    """
```

**執行動作**：
```bash
gh issue close {issue_number} --reason {reason} --comment "{comment}"
```

#### `get_milestone_progress`

```python
@mcp.tool()
def get_milestone_progress(milestone_name: str = "") -> list[dict]:
    """
    查看研究階段（milestone）的進度統計。
    不指定 milestone_name 則回傳所有階段。
    """
```

**執行動作**：
```bash
gh api repos/{owner}/{repo}/milestones \
  --jq '.[] | {title: .title, open: .open_issues, closed: .closed_issues, due: .due_on, description: .description}'
```

---

## 4. 資料模型與檔案結構

### 4.1 references/ 目錄結構

```
{project-root}/
└── references/
    ├── bibliography.bib              # 主 BibTeX 檔（所有文獻彙總）
    ├── papers/                       # 每篇文獻一個 YAML
    │   ├── vaswani2017-attention.yaml
    │   ├── brown2020-gpt3.yaml
    │   └── ...
    └── pdfs/                         # PDF 檔案（可 .gitignore）
        ├── vaswani2017-attention.pdf
        └── ...
```

### 4.2 Paper YAML Schema

```yaml
# references/papers/{key}.yaml
# ─── 基本書目資料 ───
key: "vaswani2017-attention"          # BibTeX citation key = 檔名
title: "Attention Is All You Need"
authors:
  - family: "Vaswani"
    given: "Ashish"
  - family: "Shazeer"
    given: "Noam"
year: 2017
venue: "NeurIPS"
paper_type: "conference"              # journal | conference | preprint | thesis | book | report | unknown

# ─── 識別碼與連結 ───
doi: "10.48550/arXiv.1706.03762"
url: "https://arxiv.org/abs/1706.03762"
pdf_url: "https://arxiv.org/pdf/1706.03762.pdf"
pdf_path: "pdfs/vaswani2017-attention.pdf"  # 本地相對路徑

# ─── 內容 ───
abstract: "The dominant sequence transduction models are based on complex..."
source: "arxiv"                       # arxiv | scholar | manual | semantic_scholar
categories:
  - "cs.CL"
  - "cs.AI"
keywords:
  - "transformer"
  - "attention mechanism"
  - "sequence-to-sequence"

# ─── 額外書目欄位（可選） ───
publication: ""                       # 期刊/會議全名
publisher: ""
volume: ""
issue: ""
pages: ""

# ─── AI 標註 ───
ai_annotations:
  summary: "提出 Transformer 架構，完全基於自注意力機制..."
  key_contributions:
    - "Self-attention mechanism replacing recurrence"
    - "Multi-head attention for parallel processing"
    - "Positional encoding for sequence order"
  methodology: "Encoder-decoder with multi-head self-attention layers"
  relevance_notes: "本研究的基礎架構，所有後續模型的基礎"
  tags:
    - "foundational"
    - "architecture"
  related_issues: [3, 7, 12]          # 關聯的 GitHub Issue 編號
  added_date: "2026-03-14"

# ─── 嵌入式 BibTeX ───
bibtex: |
  @inproceedings{vaswani2017attention,
    title={Attention Is All You Need},
    author={Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and others},
    booktitle={Advances in Neural Information Processing Systems},
    year={2017}
  }
```

### 4.3 GitHub Issue 結構（研究任務）

**Issue Template**（`.github/ISSUE_TEMPLATE/research-task.yml`）：

```yaml
name: Research Task
description: 建立研究任務
title: "[{PHASE}] "
labels: ["research"]
body:
  - type: dropdown
    id: phase
    attributes:
      label: 研究階段
      options:
        - Literature Review
        - Proposal
        - Experiment
        - Writing
        - Review
    validations:
      required: true

  - type: dropdown
    id: task_type
    attributes:
      label: 任務類型
      options:
        - search (搜尋)
        - read (閱讀)
        - analysis (分析)
        - code (程式碼)
        - write (撰寫)
    validations:
      required: true

  - type: textarea
    id: objective
    attributes:
      label: 研究目標
      placeholder: 描述這個任務要達成什麼...
    validations:
      required: true

  - type: textarea
    id: methodology
    attributes:
      label: 方法與步驟
      placeholder: 描述如何完成這個任務...

  - type: textarea
    id: deliverables
    attributes:
      label: 預期產出
      placeholder: 列出預期的產出物...
    validations:
      required: true

  - type: textarea
    id: references
    attributes:
      label: 相關文獻
      placeholder: 列出相關的論文 key（如 vaswani2017-attention）
```

### 4.4 OpenCode MCP 設定

`opencode.json`（使用者端）：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["python", "-m", "crane"],
      "enabled": true,
      "environment": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

## 5. 端到端研究工作流程

### 5.1 Phase 1: 專案初始化

```
使用者: "幫我初始化這個 repo 為研究專案"
   │
   ▼
CRANE 呼叫 → init_research(phases=["literature-review", "proposal", "experiment", "writing", "review"])
   │
   ├── 建立 13 個 GitHub Labels
   ├── 建立 5 個 Milestones
   ├── 建立 references/papers/, references/pdfs/
   ├── 建立 references/bibliography.bib（空檔）
   └── 建立 .github/ISSUE_TEMPLATE/research-task.yml
```

### 5.2 Phase 2: 文獻回顧

```
使用者: "搜尋關於 transformer attention mechanism 的最新論文"
   │
   ▼
AI Agent 呼叫 → search_papers(query="transformer attention mechanism", max_results=10)
   │
   ├── 回傳 10 篇論文摘要
   │
   ▼
使用者: "把前 3 篇加入文獻庫"
   │
   ▼
AI Agent 呼叫（3 次）→ add_reference(key=..., title=..., authors=..., ...)
   │                    → download_paper(paper_id=...)
   │                    → read_paper(paper_id=...)
   │                    → annotate_reference(key=..., summary=..., key_contributions=...)
   │
   ▼
AI Agent 呼叫 → create_task(
                  title="[LIT] 閱讀 transformer attention 相關論文",
                  phase="literature-review",
                  task_type="read",
                  milestone="Phase 1: Literature Review",
                  body="閱讀以下論文並整理筆記：\n- vaswani2017-attention\n- ..."
                )
   │
   ▼
（閱讀完成後）
AI Agent 呼叫 → report_progress(issue_number=1, comment="已完成 3 篇論文閱讀，重點發現：...")
              → close_task(issue_number=1, reason="completed")
```

### 5.3 Phase 3: 研究提案

```
使用者: "根據文獻回顧結果，幫我規劃研究提案的任務"
   │
   ▼
AI Agent 呼叫 → list_references(filter_tag="foundational")     # 檢視已有文獻
              → list_tasks(phase="literature-review", state="closed")  # 檢視已完成任務
   │
   ▼
AI Agent 呼叫 → create_task(title="[PROPOSAL] 定義研究問題", phase="proposal", ...)
              → create_task(title="[PROPOSAL] 設計實驗方法", phase="proposal", ...)
              → create_task(title="[PROPOSAL] 撰寫提案草稿", phase="proposal", task_type="write", ...)
```

### 5.4 Phase 4: 實驗

```
使用者: "開始實驗階段，先建立實驗設計的任務"
   │
   ▼
AI Agent 呼叫 → create_task(title="[EXP] 準備實驗環境", phase="experiment", task_type="code", ...)
              → create_task(title="[EXP] 執行 baseline 實驗", phase="experiment", ...)
              → create_task(title="[EXP] 分析實驗結果", phase="experiment", task_type="analysis", ...)
   │
   ▼
（過程中）
AI Agent 呼叫 → report_progress(issue_number=5, comment="Baseline 結果：accuracy=0.87, F1=0.82")
              → search_references(query="baseline comparison")  # 查找可比較的文獻
```

### 5.5 Phase 5: 寫作

```
使用者: "開始撰寫論文，幫我建立各章節的任務"
   │
   ▼
AI Agent 呼叫 → create_task(title="[WRITE] Introduction", phase="writing", task_type="write", ...)
              → create_task(title="[WRITE] Related Work", phase="writing", task_type="write", ...)
              → create_task(title="[WRITE] Methodology", phase="writing", task_type="write", ...)
              → create_task(title="[WRITE] Experiments", phase="writing", task_type="write", ...)
              → create_task(title="[WRITE] Conclusion", phase="writing", task_type="write", ...)
   │
   ▼
（撰寫 Related Work 時）
AI Agent 呼叫 → list_references()                               # 取得所有文獻
              → get_reference(key="vaswani2017-attention")       # 取得特定文獻詳情
              # 用 OpenCode 原生工具寫入檔案
```

### 5.6 Phase 6: 審閱

```
使用者: "建立審閱任務，檢查論文品質"
   │
   ▼
AI Agent 呼叫 → create_task(title="[REVIEW] 自我審閱 — 邏輯一致性", phase="review", ...)
              → create_task(title="[REVIEW] 自我審閱 — 引用完整性", phase="review", ...)
              → create_task(title="[REVIEW] 格式與排版檢查", phase="review", ...)
   │
   ▼
（審閱過程中）
AI Agent 呼叫 → get_milestone_progress()  # 檢視整體研究進度
```

---

## 6. SKILL.md 設計

```markdown
---
name: auto-research
description: >
  自主研究助理。用於學術研究的完整工作流程：文獻搜尋與管理、
  研究任務規劃與追蹤、論文閱讀與標註、實驗設計與分析。
  觸發詞：「搜尋論文」「加入文獻」「建立任務」「研究進度」
  「文獻回顧」「實驗設計」「撰寫論文」。
---

# Auto-Research 自主研究助理

## 核心工具

### 論文搜尋
- `search_papers` — 搜尋 arXiv 論文
- `download_paper` — 下載 PDF
- `read_paper` — 抽取全文文字

### 文獻管理
- `add_reference` — 新增文獻到 references/
- `list_references` — 列出所有文獻
- `get_reference` — 取得單篇詳情
- `search_references` — 搜尋文獻
- `remove_reference` — 刪除文獻
- `annotate_reference` — AI 標註（摘要、貢獻、方法論）

### 任務管理（GitHub Issues）
- `create_task` — 建立研究任務
- `list_tasks` — 列出任務（按階段/狀態）
- `view_task` — 查看任務詳情
- `update_task` — 更新任務
- `report_progress` — 回報進度
- `close_task` — 完成任務
- `get_milestone_progress` — 查看階段進度

### 專案管理
- `init_research` — 初始化研究專案
- `get_project_info` — 查看專案資訊

## 研究流程

### 標準工作流程
1. `init_research` → 初始化專案
2. `search_papers` → `add_reference` → `annotate_reference` → 建立文獻庫
3. `create_task` → 規劃各階段任務
4. `report_progress` → 記錄過程
5. `close_task` → 完成任務
6. `get_milestone_progress` → 追蹤整體進度

### 文獻回顧流程
1. 用 `search_papers` 搜尋相關論文
2. 用 `add_reference` 將重要論文加入文獻庫
3. 用 `download_paper` + `read_paper` 閱讀論文
4. 用 `annotate_reference` 記錄摘要和關鍵發現
5. 用 `create_task` 建立閱讀任務追蹤

### 文獻引用規則
- 所有文獻存放於 `references/papers/{key}.yaml`
- BibTeX 彙整於 `references/bibliography.bib`
- PDF 存放於 `references/pdfs/{key}.pdf`
- key 格式：`{第一作者姓}{年份}-{關鍵字}`（如 `vaswani2017-attention`）

### Issue Labels 規範
- 階段標籤：`phase:literature-review`, `phase:proposal`, `phase:experiment`, `phase:writing`, `phase:review`
- 類型標籤：`type:search`, `type:read`, `type:analysis`, `type:code`, `type:write`
- 優先權：`priority:high`, `priority:medium`, `priority:low`
```

---

## 7. MCP Server 實作結構

```
opencode-crane/
├── pyproject.toml
├── src/
│   └── crane/
│       ├── __init__.py
│       ├── server.py              # FastMCP 入口（@mcp.tool 註冊）
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── project.py         # init_research, get_project_info
│       │   ├── papers.py          # search_papers, download_paper, read_paper
│       │   ├── references.py      # add/list/get/search/remove/annotate_reference
│       │   └── tasks.py           # create/list/view/update/report/close_task, get_milestone_progress
│       ├── models/
│       │   └── paper.py           # Paper dataclass（從原 paper.py 改造）
│       └── utils/
│           ├── gh.py              # gh CLI subprocess 封裝
│           ├── git.py             # git 資訊讀取
│           ├── bibtex.py          # BibTeX 讀寫
│           └── yaml_io.py         # YAML 檔案讀寫
├── SKILL.md                       # OpenCode Skill 定義
└── README.md
```

### 7.1 server.py 入口

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("crane", json_response=True)

# 註冊所有 tools
from .tools.project import register_tools as register_project_tools
from .tools.papers import register_tools as register_paper_tools
from .tools.references import register_tools as register_reference_tools
from .tools.tasks import register_tools as register_task_tools

register_project_tools(mcp)
register_paper_tools(mcp)
register_reference_tools(mcp)
register_task_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 7.2 gh CLI 封裝

```python
# utils/gh.py
import subprocess
import json
from typing import Optional

def gh(args: list[str], json_output: bool = False) -> str | dict | list:
    """執行 gh 指令並回傳結果"""
    cmd = ["gh"] + args
    if json_output and "--json" not in args:
        pass  # caller 自行控制
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    if json_output:
        return json.loads(result.stdout)
    return result.stdout.strip()

def get_repo_info() -> dict:
    """取得當前 repo 的 owner/name"""
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True, text=True, check=True
    ).stdout.strip()
    # 解析 git@github.com:owner/repo.git 或 https://github.com/owner/repo.git
    ...
    return {"owner": owner, "repo": repo}
```

---

## 8. 依賴清單

### 8.1 Python 依賴

```toml
[project]
dependencies = [
    "mcp[cli]",           # MCP Server SDK
    "requests",           # arXiv API 呼叫
    "feedparser",         # arXiv 回應解析
    "PyPDF2",             # PDF 文字抽取
    "pyyaml",             # YAML 讀寫
    "bibtexparser",       # BibTeX 讀寫
]
```

### 8.2 系統依賴

- `gh` CLI（GitHub CLI）— 已安裝且已認證
- `git` — 已安裝
- Python 3.10+

### 8.3 移除的依賴

| 移除 | 原因 |
|------|------|
| `camel-ai` | 不再需要（OpenCode 本身是 Agent） |
| `google-adk` | 不再需要 |
| `openai-agents` | 不再需要 |
| `sqlite3` | 改用檔案式管理 |
| `sciagents` | 不再需要（隱性依賴，非公開套件） |
| `fastapi` / `uvicorn` | MCP Server 取代 |
| `pydantic` | MCP SDK 自帶驗證 |

---

## 9. 與原架構的對照總結

| 維度 | 原設計 | 新設計 |
|------|--------|--------|
| **執行環境** | FastAPI server + Web UI | MCP Server（stdio transport） |
| **AI 引擎** | sciagents ChatAgent | OpenCode 本身（Claude/GPT） |
| **專案識別** | YAML 設定檔 + workspace 路徑 | git repo = 專案 |
| **任務管理** | 前端 Planner stub | GitHub Issues via `gh` CLI |
| **文獻儲存** | 雙 SQLite DB | `references/` 目錄（YAML + BibTeX） |
| **論文搜尋** | Agent 內建工具 | MCP Tool |
| **PDF 處理** | Agent 內建工具 | MCP Tool |
| **串流回應** | SSE / WebSocket | MCP progress reporting |
| **工具註冊** | `FunctionTool` + AgentFactory | `@mcp.tool()` decorator |
| **設定管理** | `config/config.yml` | `opencode.json` MCP 區塊 |
| **前端** | Vanilla HTML/JS/CSS | CLI（OpenCode TUI） |
| **協作** | 無 | GitHub Issues + PR（原生支援） |

---

## 10. TDD 開發流程

### 10.1 測試架構

```
tests/
├── conftest.py                 # 共用 fixtures（mock gh/git、temp dir、sample data）
├── models/
│   └── test_paper.py           # Paper + AiAnnotations 資料模型
├── utils/
│   ├── test_yaml_io.py         # YAML 讀寫
│   ├── test_bibtex.py          # BibTeX 讀寫
│   ├── test_gh.py              # gh CLI subprocess 封裝
│   └── test_git.py             # git 資訊讀取
├── tools/
│   ├── test_project.py         # init_research, get_project_info
│   ├── test_papers.py          # search/download/read_paper
│   ├── test_references.py      # add/list/get/search/remove/annotate_reference
│   └── test_tasks.py           # create/list/view/update/report/close_task
└── integration/
    └── test_workflow.py        # 端到端工作流程
```

### 10.2 RED → GREEN → REFACTOR 循環

**開發順序（由內而外）**：

| 順序 | 模組 | 測試數 | 說明 |
|------|------|--------|------|
| 1 | `models/paper.py` | 15 | 純資料模型，零外部依賴 |
| 2 | `utils/yaml_io.py` | 11 | 檔案 I/O，只依賴 PyYAML |
| 3 | `utils/bibtex.py` | 9 | BibTeX 讀寫，只依賴 bibtexparser |
| 4 | `utils/gh.py` | 6 | subprocess 封裝，mock 測試 |
| 5 | `utils/git.py` | 6 | subprocess 封裝，mock 測試 |
| 6 | `tools/references.py` | 12 | 組合 yaml_io + bibtex |
| 7 | `tools/papers.py` | 7 | 組合 arXiv API + yaml_io |
| 8 | `tools/tasks.py` | 14 | 組合 gh CLI wrapper |
| 9 | `tools/project.py` | 9 | 組合 gh + git + filesystem |
| 10 | `integration/` | 9 | 端到端驗證 |

**每個模組的開發步驟**：

```
1. RED:   執行 pytest tests/models/test_paper.py — 全部 FAIL（NotImplementedError）
2. GREEN: 實作 src/crane/models/paper.py — 讓測試通過
3. REFACTOR: 清理程式碼，保持測試綠燈
4. 下一個模組
```

### 10.3 測試 Mocking 策略

| 外部依賴 | Mock 方式 | Fixture |
|----------|----------|---------|
| `gh` CLI | `MockGhCli` 類（記錄呼叫 + 預設回應） | `mock_gh` |
| `git` 指令 | `MockGitInfo` 類（預設 owner/repo/branch） | `mock_git` |
| arXiv API | XML 字串常量 | `mock_arxiv_response` |
| 檔案系統 | `pytest tmp_path` + `tmp_project` fixture | `tmp_project`, `papers_dir`, `bib_path` |
| PDF 讀取 | Mock PyPDF2 reader | 按需 patch |

### 10.4 Make 指令

```bash
make install          # 安裝套件 + dev 依賴
make test             # 跑全部測試
make test-unit        # 只跑單元測試（跳過 integration）
make test-integration # 只跑整合測試
make test-cov         # 跑測試 + 覆蓋率報告（目標 ≥80%）
make lint             # 跑 ruff 檢查
make fmt              # 格式化程式碼
```

---

## 11. Event Hook 介面設計（Future Work）

> 本節僅定義介面規格，不實作程式碼。當需要無人值守的自動化反應時再行實作。

### 11.1 Event Schema

每個事件包含以下欄位：

```python
@dataclass
class CraneEvent:
    event_type: str       # e.g. "paper_added", "task_closed"
    timestamp: str        # ISO 8601
    source_tool: str      # 觸發此事件的 tool 名稱
    payload: dict         # 事件特定資料
```

### 11.2 事件類型

| event_type | source_tool | payload | 觸發時機 |
|---|---|---|---|
| paper_added | add_reference | {key, title, authors} | 論文加入文獻庫 |
| paper_annotated | annotate_reference | {key, summary} | 論文標註完成 |
| paper_removed | remove_reference | {key} | 論文從文獻庫移除 |
| task_created | create_task | {number, title, phase} | GitHub Issue 建立 |
| task_closed | close_task | {number, reason} | GitHub Issue 關閉 |
| milestone_completed | close_task | {milestone_title} | Milestone 所有 Issue 關閉 |
| pipeline_completed | run_pipeline | {pipeline, completed_steps, artifacts} | Pipeline 成功完成 |
| pipeline_failed | run_pipeline | {pipeline, failed_step, error} | Pipeline 執行失敗 |

### 11.3 Hook 配置格式

```yaml
# .crane/hooks.yml (未來)
hooks:
  - on: paper_added
    do: [download_paper, read_paper, annotate_reference]
    condition: "payload.source == 'arxiv'"

  - on: task_closed
    do: [get_milestone_progress]

  - on: pipeline_failed
    do: [report_progress]
    with:
      comment: "Pipeline failed at {payload.failed_step}: {payload.error}"
```

### 11.4 實作考量

- Hook 執行應為非同步，不阻塞主流程
- 需要防止無限迴圈（hook A 觸發 hook B 觸發 hook A）
- 每個 hook 需要超時和重試策略
- 建議先從「通知型」hook（只 report_progress）開始，再擴充「動作型」hook
