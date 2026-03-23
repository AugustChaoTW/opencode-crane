# CRANE 安裝指南

## 系統需求

| 項目 | 需求 |
|------|------|
| 作業系統 | Ubuntu 20.04+, Rocky Linux 8+, RHEL 8+, Fedora 36+ |
| Python | 3.10+ |
| Git | 2.0+ |
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

在 `~/.config/opencode/opencode.json` 中新增：

```bash
mkdir -p ~/.config/opencode
cat > ~/.config/opencode/opencode.json << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
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

**⚠️ 注意**：使用 `sh -c` 包裝命令，不要使用 `cwd` 參數。

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

## 解除安裝

```bash
# 刪除 CRANE
rm -rf ~/.opencode-crane

# 刪除配置
rm -rf ~/.config/opencode/plugins/memory-system
rm ~/.config/opencode/skills/opencode-crane

# 清理 MCP 配置（手動編輯 ~/.config/opencode/opencode.json）
```

---

## 支援

- GitHub Issues: https://github.com/AugustChaoTW/opencode-crane/issues
- 文件: https://github.com/AugustChaoTW/opencode-crane/blob/main/README.md
