# opencode-crane

**CRANE** — 自主研究助理 MCP Server，專為 [OpenCode](https://github.com/anomalyco/opencode) 設計。

將完整的學術研究工作流程（文獻搜尋 → 提案 → 實驗 → 寫作 → 審閱）整合為一組 MCP 工具，透過 GitHub Issues 追蹤任務，以檔案式管理（YAML + BibTeX）維護引用文獻。

> **CRANE**（鶴）：象徵智慧、耐心與精準。鶴耐心觀察水面，一擊命中——正如研究者深度閱讀文獻後精準提取洞見。

---

## 專案背景

本專案前身為 [Auto-Research](https://github.com/universea/Auto-Research)（Autonomous Generalist Scientist），一個以 FastAPI + Web UI + SQLite 為基礎的自動化研究框架。原始設計採用獨立的 Web 服務架構，具備 Agent 聊天、論文搜尋、專案管理等功能。

**opencode-crane** 是對原架構的徹底重新設計：

| 維度 | 原設計（Auto-Research） | 新設計（CRANE） |
|------|----------------------|----------------|
| 執行環境 | FastAPI server + Web UI | Python MCP Server（stdio） |
| AI 引擎 | sciagents ChatAgent | OpenCode 本身（Claude / GPT） |
| 專案管理 | YAML 設定檔 + workspace 路徑 | Git repo = 專案 |
| 任務管理 | 前端 Planner（stub） | GitHub Issues via `gh` CLI |
| 文獻儲存 | 雙 SQLite DB | `references/` 目錄（YAML + BibTeX） |
| 工具註冊 | `FunctionTool` + AgentFactory | `@mcp.tool()` decorator |
| 前端 | Vanilla HTML/JS/CSS | CLI（OpenCode TUI） |
| 協作 | 無 | GitHub Issues + PR（原生支援） |

舊版程式碼封存於 `_archive/` 目錄中供參考。

---

## 功能總覽

### 18 個 MCP Tools，分 4 大類

#### 專案管理（2 tools）
| Tool | 說明 |
|------|------|
| `init_research` | 初始化 GitHub repo 為研究專案：建立 phase/type/priority labels、milestones、`references/` 目錄、Issue Template |
| `get_project_info` | 取得專案資訊：repo 名稱、branch、最近 commit、milestone 進度、文獻數量 |

#### 論文搜尋（3 tools）
| Tool | 說明 |
|------|------|
| `search_papers` | 搜尋 arXiv 學術論文，回傳 title / authors / abstract / DOI / PDF URL |
| `download_paper` | 下載論文 PDF 到 `references/pdfs/` |
| `read_paper` | 讀取 PDF 並抽取全文純文字（若不存在會自動下載） |

#### 文獻管理（6 tools）
| Tool | 說明 |
|------|------|
| `add_reference` | 新增文獻：寫入 `references/papers/{key}.yaml` + 追加到 `bibliography.bib` |
| `list_references` | 列出所有文獻，支援 keyword/tag 篩選 |
| `get_reference` | 取得單篇文獻完整詳情（含 AI 標註） |
| `search_references` | 全文搜尋文獻的 title / authors / abstract / keywords |
| `remove_reference` | 刪除文獻（YAML + BibTeX 條目 + 可選刪 PDF） |
| `annotate_reference` | 為文獻新增 AI 標註：摘要、關鍵貢獻、方法論、相關 Issue |

#### 任務管理（7 tools）
| Tool | 說明 | 底層指令 |
|------|------|---------|
| `create_task` | 建立研究任務（GitHub Issue），自動加 phase/type/priority labels | `gh issue create` |
| `list_tasks` | 列出任務，按 phase / state / milestone 篩選 | `gh issue list --json` |
| `view_task` | 查看單個任務完整內容與留言歷史 | `gh issue view --json` |
| `update_task` | 更新任務標題、標籤、milestone、指派人 | `gh issue edit` |
| `report_progress` | 在任務上留言回報進度 | `gh issue comment` |
| `close_task` | 完成任務（reason: completed / not_planned） | `gh issue close` |
| `get_milestone_progress` | 查看研究階段 milestone 的進度統計 | `gh api milestones` |

---

## 研究工作流程

CRANE 支援完整的研究生命週期，每個階段都有對應的工具和 GitHub Issue 追蹤：

```
Phase 1: 初始化
  init_research → 建立 labels / milestones / references 目錄

Phase 2: 文獻回顧
  search_papers → add_reference → download_paper → read_paper → annotate_reference
  create_task(phase="literature-review") → report_progress → close_task

Phase 3: 研究提案
  list_references → create_task(phase="proposal")
  用 OpenCode 原生工具撰寫提案文件

Phase 4: 實驗
  create_task(phase="experiment") → report_progress
  用 OpenCode 原生 Shell 執行實驗

Phase 5: 寫作
  get_reference → list_references → create_task(phase="writing")
  用 OpenCode 原生檔案工具撰寫論文

Phase 6: 審閱
  create_task(phase="review") → get_milestone_progress
  全流程進度追蹤
```

---

## 資料管理

### 文獻儲存結構

```
{project-root}/
└── references/
    ├── bibliography.bib            # 主 BibTeX 檔（所有文獻彙總，學術工具互通）
    ├── papers/                     # 每篇文獻一個 YAML（AI 友善結構化元資料）
    │   ├── vaswani2017-attention.yaml
    │   ├── brown2020-gpt3.yaml
    │   └── ...
    └── pdfs/                       # PDF 檔案（已加入 .gitignore）
        ├── vaswani2017-attention.pdf
        └── ...
```

### Paper YAML 格式

每篇文獻以 `{第一作者姓}{年份}-{關鍵字}` 為 key（例如 `vaswani2017-attention`），包含：

- **書目資料**：title, authors, year, venue, doi, url, pdf_url, abstract
- **分類**：paper_type, categories, keywords, source
- **AI 標註**（`ai_annotations`）：summary, key_contributions, methodology, relevance_notes, tags, related_issues
- **嵌入式 BibTeX**：直接內嵌對應的 BibTeX 條目

### 任務追蹤（GitHub Issues）

透過 Label 和 Milestone 組織研究任務：

| Label 類別 | 值 |
|-----------|-----|
| 研究階段 | `phase:literature-review`, `phase:proposal`, `phase:experiment`, `phase:writing`, `phase:review` |
| 任務類型 | `type:search`, `type:read`, `type:analysis`, `type:code`, `type:write` |
| 優先權 | `priority:high`, `priority:medium`, `priority:low` |

每個研究階段對應一個 Milestone，可追蹤完成進度。

---

## 安裝

### 系統需求

- Python 3.10+
- [GitHub CLI (`gh`)](https://cli.github.com/) — 已安裝且已認證（`gh auth login`）
- Git

### 安裝步驟

```bash
# 複製專案
git clone https://github.com/augchao/auto-research.git
cd auto-research

# 安裝套件（含 dev 依賴）
pip install -e ".[dev]"
```

### OpenCode 設定

在你的 OpenCode 設定檔中加入 CRANE MCP server：

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

也可將 `SKILL.md` 複製到 OpenCode 的 skills 目錄：

```bash
# 使用者級 skill
cp SKILL.md ~/.config/opencode/skills/opencode-crane/SKILL.md

# 或專案級 skill
mkdir -p .opencode/skills/opencode-crane
cp SKILL.md .opencode/skills/opencode-crane/SKILL.md
```

---

## 開發

### TDD 開發流程

本專案採用 **Test-Driven Development**。所有測試已預先定義期望行為（RED 階段），每個模組的實作流程為：

```
1. RED:      pytest tests/models/test_paper.py  → 全部 FAIL
2. GREEN:    實作 src/crane/models/paper.py     → 讓測試通過
3. REFACTOR: 清理程式碼，保持綠燈
```

### 開發順序（由內而外）

| 順序 | 模組 | 測試數 | 說明 |
|------|------|--------|------|
| 1 | `models/paper.py` | 15 | 純資料模型，零外部依賴 |
| 2 | `utils/yaml_io.py` | 11 | YAML 讀寫，只依賴 PyYAML |
| 3 | `utils/bibtex.py` | 9 | BibTeX 讀寫，只依賴 bibtexparser |
| 4 | `utils/gh.py` | 6 | `gh` CLI subprocess 封裝 |
| 5 | `utils/git.py` | 6 | git info subprocess 封裝 |
| 6 | `tools/references.py` | 12 | 組合 yaml_io + bibtex |
| 7 | `tools/papers.py` | 7 | 組合 arXiv API + yaml_io |
| 8 | `tools/tasks.py` | 14 | 組合 gh CLI wrapper |
| 9 | `tools/project.py` | 9 | 組合 gh + git + filesystem |
| 10 | `integration/` | 9 | 端到端工作流程驗證 |

### Make 指令

```bash
make install          # 安裝套件 + dev 依賴
make test             # 跑全部測試
make test-unit        # 只跑單元測試（跳過 integration）
make test-integration # 只跑整合測試
make test-cov         # 跑測試 + 覆蓋率報告（目標 >= 80%）
make lint             # Ruff 程式碼檢查
make fmt              # Ruff 程式碼格式化
```

### 專案結構

```
opencode-crane/
├── pyproject.toml                  # 專案設定（hatch + pytest-cov + ruff）
├── Makefile                        # 開發指令
├── SKILL.md                        # OpenCode Skill 定義
├── OPENCODE_GH_FEAT_DESIGN.md      # 完整設計規格書
│
├── src/crane/                      # 主套件
│   ├── __init__.py                 # 版本、專案名
│   ├── __main__.py                 # python -m crane 入口
│   ├── server.py                   # FastMCP server，註冊 18 個 tools
│   ├── models/
│   │   └── paper.py                # Paper + AiAnnotations dataclass
│   ├── tools/
│   │   ├── project.py              # init_research, get_project_info
│   │   ├── papers.py               # search_papers, download_paper, read_paper
│   │   ├── references.py           # add/list/get/search/remove/annotate_reference
│   │   └── tasks.py                # create/list/view/update/report/close_task
│   └── utils/
│       ├── gh.py                   # gh CLI subprocess 封裝
│       ├── git.py                  # git 資訊讀取
│       ├── bibtex.py               # BibTeX 讀寫
│       └── yaml_io.py              # YAML 檔案讀寫
│
├── tests/                          # TDD 測試（鏡射 src/crane/）
│   ├── conftest.py                 # 共用 fixtures
│   ├── models/test_paper.py        # Paper 資料模型測試
│   ├── utils/                      # 工具函式測試
│   │   ├── test_yaml_io.py
│   │   ├── test_bibtex.py
│   │   ├── test_gh.py
│   │   └── test_git.py
│   ├── tools/                      # MCP Tool 測試
│   │   ├── test_project.py
│   │   ├── test_papers.py
│   │   ├── test_references.py
│   │   └── test_tasks.py
│   └── integration/
│       └── test_workflow.py        # 端到端流程測試
│
├── _archive/                       # 舊版程式碼封存（供參考）
│   ├── gscientist/                 # 原 agent/server/references/tools
│   ├── ui/                         # 原 Web UI
│   ├── config/                     # 原 YAML 設定檔
│   └── tests/                      # 原測試
│
└── docs/                           # 文件與圖片
```

### 依賴清單

**Runtime**：
- `mcp[cli]` — MCP Server SDK
- `requests` — arXiv API 呼叫
- `feedparser` — arXiv 回應解析
- `PyPDF2` — PDF 文字抽取
- `pyyaml` — YAML 讀寫
- `bibtexparser` — BibTeX 讀寫

**Dev**：
- `pytest` — 測試框架
- `pytest-cov` — 覆蓋率報告
- `ruff` — Linter + Formatter

**系統**：
- `gh` CLI（GitHub CLI）
- `git`

---

## 設計文件

完整的功能設計規格請參閱 [`OPENCODE_GH_FEAT_DESIGN.md`](./OPENCODE_GH_FEAT_DESIGN.md)，包含：

1. 架構總覽與設計決策
2. 原始功能盤點（對照研究流程 5 階段）
3. 18 個 MCP Tool 的完整簽章與執行邏輯
4. Paper YAML Schema 與 Issue Template 設計
5. 端到端研究工作流程（6 個階段的互動腳本）
6. SKILL.md 內容設計
7. MCP Server 實作結構
8. 依賴管理
9. 新舊架構對照表
10. TDD 開發流程與測試策略

---

## 授權

MIT License

## 引用

```bibtex
@article{zhang2025scaling,
  title={Scaling Laws in Scientific Discovery with AI and Robot Scientists},
  author={Zhang, Pengsong and Zhang, Heng and Xu, Huazhe and Xu, Renjun and Wang, Zhenting and Wang, Cong and Garg, Animesh and Li, Zhibin and Ajoudani, Arash and Liu, Xinyu},
  journal={arXiv preprint arXiv:2503.22444},
  year={2025}
}
```
