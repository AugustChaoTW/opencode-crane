# opencode-crane

**CRANE** — 自主研究助理 MCP Server，專為 [OpenCode](https://github.com/anomalyco/opencode) 設計。

將完整的學術研究工作流程（文獻搜尋 → 提案 → 實驗 → 寫作 → 審閱）整合為一組 MCP 工具，透過 GitHub Issues 追蹤任務，以檔案式管理（YAML + BibTeX）維護引用文獻。

> **CRANE**（鶴）：象徵智慧、耐心與精準。鶴耐心觀察水面，一擊命中——正如研究者深度閱讀文獻後精準提取洞見。

---

## 主要功能

- **論文搜尋與閱讀** — 搜尋 arXiv、下載 PDF、自動抽取全文
- **文獻庫管理** — YAML + BibTeX 雙格式儲存，支援搜尋、篩選、AI 標註
- **研究任務追蹤** — 透過 GitHub Issues 管理任務，自動建立 labels / milestones
- **研究階段管理** — 文獻回顧 → 提案 → 實驗 → 寫作 → 審閱，全程追蹤進度
- **專案初始化** — 一鍵設定研究專案結構（labels、milestones、目錄、Issue Template）
- **OpenCode 原生整合** — MCP Server 架構，AI agent 透過自然語言直接操作

```
你說：「搜尋 transformer 相關的論文，把前 3 篇加入文獻庫，建立閱讀任務」

crane 會：
  1. search_papers("transformer")       → 搜尋 arXiv
  2. add_reference(...)  ×3             → 寫入 YAML + BibTeX
  3. download_paper(...) ×3             → 下載 PDF
  4. annotate_reference(...) ×3         → AI 摘要標註
  5. create_task(phase="literature-review") → 建立 GitHub Issue
```

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

在安裝前，先確認以下工具可用：

```bash
# 檢查 Python 版本（需要 3.10+）
python3 --version

# 檢查 git
git --version

# 檢查 GitHub CLI（任務管理需要）
gh --version
gh auth status
```

如果 `gh` 未安裝，請參考 https://cli.github.com/ 安裝。
如果 `gh` 未認證，執行 `gh auth login`。

### Step 1: 安裝 crane

```bash
# Clone 到 ~/.opencode-crane（標準安裝位置）
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane

# 建立虛擬環境並安裝
cd ~/.opencode-crane
python3 -m venv .venv
.venv/bin/pip install -e .
```

**驗證**：

```bash
~/.opencode-crane/.venv/bin/python -c "
from crane.server import mcp
tools = mcp._tool_manager._tools
print(f'OK: {len(tools)} tools registered')
for name in sorted(tools): print(f'  - {name}')
"
```

預期輸出：`OK: 18 tools registered`，列出所有 tool 名稱。

### Step 2: 設定專案 MCP

在你的研究專案根目錄執行：

```bash
# 建立 .opencode 目錄和 MCP 設定
mkdir -p .opencode

cat > .opencode/opencode.json << 'MCPEOF'
{
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["~/.opencode-crane/.venv/bin/python", "-m", "crane"],
      "enabled": true
    }
  }
}
MCPEOF
```

> **注意**：如果你的專案已有 `.opencode/opencode.json`，請手動將 `crane` 區塊
> 合併到現有的 `mcp` 物件中，而非覆蓋整個檔案。

### Step 3: 安裝 SKILL.md（建議）

SKILL.md 告訴 AI agent 何時以及如何使用 crane 工具：

```bash
mkdir -p .opencode/skills/opencode-crane
cp ~/.opencode-crane/SKILL.md .opencode/skills/opencode-crane/SKILL.md
```

### Step 4: 設定 .gitignore

確保 PDF 檔案不被追蹤：

```bash
# 如果 .gitignore 中還沒有這行，加上去
grep -q "references/pdfs/" .gitignore 2>/dev/null || echo "references/pdfs/" >> .gitignore
```

### Step 5: 驗證

重新啟動 OpenCode，然後輸入：

```
幫我初始化這個 repo 為研究專案
```

如果 crane 正確安裝，AI agent 會呼叫 `init_research` 工具，你會看到：
- GitHub labels 被建立（`phase:literature-review` 等）
- Milestones 被建立
- `references/` 目錄被建立

### 或用腳本一步完成（Step 2-4）

```bash
bash ~/.opencode-crane/scripts/setup-project.sh
```

<!-- OPENCODE-INSTALL-GUIDE-END -->

---

## 更新

```bash
cd ~/.opencode-crane
git pull
.venv/bin/pip install -e .
```

---

## 功能總覽

### 18 個 MCP Tools，分 4 大類

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

#### 任務管理（7 tools）
| Tool | 說明 | 底層 |
|------|------|------|
| `create_task` | 建立研究任務（GitHub Issue），自動加 labels | `gh issue create` |
| `list_tasks` | 列出任務，按階段 / 狀態 / milestone 篩選 | `gh issue list` |
| `view_task` | 查看單個任務內容與留言歷史 | `gh issue view` |
| `update_task` | 更新任務標籤、milestone、指派人 | `gh issue edit` |
| `report_progress` | 在任務上留言回報進度 | `gh issue comment` |
| `close_task` | 完成任務 | `gh issue close` |
| `get_milestone_progress` | 查看各研究階段的進度統計 | `gh api` |

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

### 任務管理

```
> 建立一個文獻回顧任務：閱讀 5 篇 attention 相關論文
> 目前的任務進度如何？
> 標記任務 #1 為已完成
```

### 查看進度

```
> 顯示整體研究進度
> 列出所有文獻
> 搜尋有關 self-attention 的文獻
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
  get_reference → create_task(phase="writing")

Phase 6: 審閱
  create_task(phase="review") → get_milestone_progress
```

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

### GitHub Issues 標籤

| 類別 | Labels |
|------|--------|
| 研究階段 | `phase:literature-review` `phase:proposal` `phase:experiment` `phase:writing` `phase:review` |
| 任務類型 | `type:search` `type:read` `type:analysis` `type:code` `type:write` |
| 優先權 | `priority:high` `priority:medium` `priority:low` |

---

## 開發

```bash
cd ~/.opencode-crane
pip install -e ".[dev]"

make test             # 141 tests
make test-cov         # 覆蓋率 93.78%
make lint             # ruff 檢查
make fmt              # 格式化
```

### 專案結構

```
opencode-crane/
├── pyproject.toml
├── Makefile
├── SKILL.md                        # OpenCode Skill 定義
├── OPENCODE_GH_FEAT_DESIGN.md      # 完整設計規格書
├── scripts/
│   ├── install.sh                  # 一鍵安裝
│   └── setup-project.sh            # 專案設定
├── src/crane/                      # 主套件
│   ├── server.py                   # MCP Server 入口
│   ├── models/paper.py             # Paper + AiAnnotations
│   ├── tools/{project,papers,references,tasks}.py
│   └── utils/{gh,git,bibtex,yaml_io}.py
├── tests/                          # 141 tests（93.78% coverage）
└── _archive/                       # 舊版程式碼封存
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
