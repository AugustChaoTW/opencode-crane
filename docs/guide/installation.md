# CRANE 安裝指南

## 系統需求

| 項目 | 需求 |
|------|------|
| 作業系統 | Ubuntu 20.04+, Rocky Linux 8+, RHEL 8+, Fedora 36+ |
| Python | 3.10+ |
| Git | 2.0+ |
| bun | 最新版（Plugin 安裝需要）|
| GitHub CLI | 可選（任務管理需要） |

---

## 一鍵安裝（推薦）

```bash
curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash
```

安裝腳本會自動：
1. 偵測作業系統
2. 安裝系統依賴（git、curl）
3. 安裝 uv（Python 套件管理器）
4. 安裝 GitHub CLI（可選）
5. Clone 專案
6. `uv sync` 安裝依賴
7. 驗證安裝

---

## 手動安裝

### Step 1: 安裝 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: 安裝 crane

```bash
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
cd ~/.opencode-crane
uv sync
```

### Step 3: 驗證

```bash
uv run python -c "
from crane.server import mcp
tools = mcp._tool_manager._tools
print(f'OK: {len(tools)} tools registered')
"
```

---

## 設定 MCP

### 方式 1：專案配置（推薦）

在你的研究專案根目錄建立 `.opencode/opencode.json`：

```bash
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
```

### 方式 2：全域配置

一鍵安裝腳本會自動建立全域配置（含 Plugin），位於 `~/.config/opencode/opencode.json`。

---

## Plugin 安裝

CRANE 安裝腳本會自動安裝以下 3 個 OpenCode Plugin 到 `~/.config/opencode/`：

| Plugin | 來源 | 功能 |
|--------|------|------|
| oh-my-opencode (omo) | npm | Agent 增強框架 |
| opencode-claude-auth | npm | Claude Code 認證整合 |
| memory-system | GitHub clone + build | Agent 持久化記憶系統 |

### 自動安裝

一鍵安裝腳本已整合 Plugin 安裝，無需額外步驟。

### 手動安裝

如果自動安裝失敗或需要個別安裝：

```bash
cd ~/.config/opencode

# 1. npm plugins
cat > package.json << 'EOF'
{
  "dependencies": {
    "@opencode-ai/plugin": "^1.3.2",
    "oh-my-opencode": "^3.12.3",
    "opencode-claude-auth": "^1.3.1"
  }
}
EOF
bun install

# 2. memory-system
git clone --depth 1 https://github.com/AugustChaoTW/aug-money.git /tmp/aug-money
cd /tmp/aug-money/opencode-memory-system && bun install && bun run build
mkdir -p ~/.config/opencode/plugins/memory-system
cp dist/index.js dist/sql-wasm.wasm package.json ~/.config/opencode/plugins/memory-system/
rm -rf /tmp/aug-money
```

### Plugin 配置

`~/.config/opencode/opencode.json` 中需包含 `plugin` 陣列：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "oh-my-opencode",
    "opencode-claude-auth",
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
```

oh-my-opencode 需要額外配置檔 `~/.config/opencode/oh-my-opencode.json`：

```json
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json",
  "google_auth": false,
  "agents": {}
}
```

---

## 安裝 SKILL.md（建議）

SKILL.md 告訴 AI agent 何時以及如何使用 CRANE 工具：

```bash
mkdir -p .opencode/skills/opencode-crane
cp ~/.opencode-crane/SKILL.md .opencode/skills/opencode-crane/SKILL.md
```

---

## 設定 .gitignore

確保 PDF 檔案不被追蹤：

```bash
echo "references/pdfs/" >> .gitignore
echo "papers/*/figures/*.pdf" >> .gitignore
```

---

## 安裝 GitHub CLI（可選）

CRANE 使用 GitHub Issues 追蹤任務。如需此功能：

### Ubuntu/Debian

```bash
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

### Rocky/RHEL/Fedora

```bash
sudo dnf install 'dnf-command(config-manager)'
sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
sudo dnf install gh
```

### 認證

```bash
gh auth login
```

---

## 更新

```bash
cd ~/.opencode-crane
git pull
uv sync
```

---

## 驗證安裝

### 檢查 MCP Server

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | timeout 2 ~/.opencode-crane/.venv/bin/crane
```

預期輸出：
```json
{"result":{"serverInfo":{"name":"crane","version":"1.26.0"}}}
```

### 檢查工具數量

```bash
cd ~/.opencode-crane && uv run python -c "
from crane.server import mcp
tools = mcp._tool_manager._tools
print(f'Tools: {len(tools)}')
for name in sorted(tools):
    print(f'  - {name}')
"
```

預期：30 個工具

---

## 啟動 OpenCode

```bash
# 在你的研究專案目錄
cd ~/your-research-project

# 啟動 OpenCode
opencode
```

然後輸入：

```
> 幫我初始化這個 repo 為研究專案
```

如果 CRANE 正確安裝，AI agent 會呼叫 `init_research` 工具。

---

## 常見問題

### Q: MCP Server 啟動失敗

**錯誤**：`ENOENT: no such file or directory`

**原因**：配置中的路徑錯誤

**解決**：確保使用 `sh -c` 包裝命令：
```json
"command": ["sh", "-c", "cd $HOME/.opencode-crane && uv run crane"]
```

### Q: 工具數量不符預期

**檢查**：
```bash
cd ~/.opencode-crane && uv run python -c "
from crane.server import mcp
print(len(mcp._tool_manager._tools))
"
```

**解決**：重新安裝
```bash
cd ~/.opencode-crane
git pull
uv sync
```

### Q: GitHub CLI 未認證

**錯誤**：`gh: not logged into any GitHub hosts`

**解決**：
```bash
gh auth login
```

### Q: Python 版本過舊

**錯誤**：`Python 3.10+ required`

**解決**：安裝 Python 3.12
```bash
# Ubuntu
sudo apt install python3.12

# Rocky/RHEL
sudo dnf install python3.12
```

---

## 安裝檢查清單

- [ ] uv 已安裝（`command -v uv`）
- [ ] bun 已安裝（`command -v bun`）
- [ ] `~/.opencode-crane/.venv` 存在（CRANE 本體）
- [ ] `~/.config/opencode/package.json` 存在
- [ ] `~/.config/opencode/node_modules/oh-my-opencode` 存在
- [ ] `~/.config/opencode/node_modules/opencode-claude-auth` 存在
- [ ] `~/.config/opencode/plugins/memory-system/index.js` 存在
- [ ] `~/.config/opencode/opencode.json` 包含 `plugin` 陣列
- [ ] `~/.config/opencode/oh-my-opencode.json` 存在
- [ ] `~/.config/opencode/skills/opencode-crane/SKILL.md` 存在
- [ ] 專案 `.opencode/opencode.json` 已設定 MCP（crane）
- [ ] 專案 `.gitignore` 包含 `references/pdfs/`

---

## 解除安裝

```bash
rm -rf ~/.opencode-crane
rm -rf ~/.config/opencode/plugins/memory-system
rm -f ~/.config/opencode/skills/opencode-crane/SKILL.md
rm -f ~/.config/opencode/oh-my-opencode.json
# 清理 npm plugins: cd ~/.config/opencode && bun install
```

---

## 支援

- GitHub Issues: https://github.com/AugustChaoTW/opencode-crane/issues
- 文件: https://github.com/AugustChaoTW/opencode-crane/blob/main/README.md
