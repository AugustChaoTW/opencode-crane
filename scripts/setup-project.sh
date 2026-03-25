#!/usr/bin/env bash
# ============================================================================
# opencode-crane project setup
#
# Run this INSIDE your research project repo to configure crane.
# Assumes crane is already installed at ~/.opencode-crane
#
# Usage:
#   bash ~/.opencode-crane/scripts/setup-project.sh
# ============================================================================
set -euo pipefail

INSTALL_DIR="${CRANE_INSTALL_DIR:-$HOME/.opencode-crane}"
VENV_DIR="$INSTALL_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
OPENCODE_CONFIG_DIR="$HOME/.config/opencode"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[crane]${NC} $*"; }
ok()    { echo -e "${GREEN}[crane]${NC} $*"; }
err()   { echo -e "${RED}[crane]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
if [ ! -f "$PYTHON_BIN" ]; then
    err "crane not installed. Run install.sh first:"
    err "  curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash"
    exit 1
fi

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    err "Not inside a git repo. Run this from your research project root."
    exit 1
fi

PROJECT_ROOT=$(git rev-parse --show-toplevel)
info "Setting up crane for: $PROJECT_ROOT"

# ---------------------------------------------------------------------------
# 1. MCP config
# ---------------------------------------------------------------------------
MCP_DIR="$PROJECT_ROOT/.opencode"
MCP_FILE="$MCP_DIR/opencode.json"

mkdir -p "$MCP_DIR"

if [ -f "$MCP_FILE" ]; then
    info "MCP config exists at $MCP_FILE, checking for crane..."
    if grep -q '"crane"' "$MCP_FILE"; then
        ok "crane already configured in MCP"
    else
        err "MCP config exists but crane not found. Add manually:"
        echo '  "crane": { "type": "local", "command": ["'"$PYTHON_BIN"'", "-m", "crane"], "enabled": true }'
    fi
else
    cat > "$MCP_FILE" << EOF
{
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["$PYTHON_BIN", "-m", "crane"],
      "enabled": true
    }
  }
}
EOF
    ok "Created $MCP_FILE"
fi

# ---------------------------------------------------------------------------
# 2. SKILL.md
# ---------------------------------------------------------------------------
SKILL_DIR="$MCP_DIR/skills/opencode-crane"
mkdir -p "$SKILL_DIR"
cp "$INSTALL_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
ok "Installed SKILL.md → $SKILL_DIR/SKILL.md"

# ---------------------------------------------------------------------------
# 3. .gitignore additions
# ---------------------------------------------------------------------------
GITIGNORE="$PROJECT_ROOT/.gitignore"
if [ -f "$GITIGNORE" ]; then
    if ! grep -q "references/pdfs/" "$GITIGNORE"; then
        echo "" >> "$GITIGNORE"
        echo "# opencode-crane" >> "$GITIGNORE"
        echo "references/pdfs/" >> "$GITIGNORE"
        ok "Added references/pdfs/ to .gitignore"
    fi
else
    echo "# opencode-crane" > "$GITIGNORE"
    echo "references/pdfs/" >> "$GITIGNORE"
    ok "Created .gitignore with references/pdfs/"
fi

# ---------------------------------------------------------------------------
# 4. Plugin package.json (project-level)
# ---------------------------------------------------------------------------
PKG_FILE="$MCP_DIR/package.json"
if [ -f "$PKG_FILE" ]; then
    ok "package.json already exists at $PKG_FILE"
else
    cat > "$PKG_FILE" << 'PKGEOF'
{
  "dependencies": {
    "@opencode-ai/plugin": "^1.3.2",
    "oh-my-opencode": "^3.12.3",
    "opencode-claude-auth": "^1.3.1"
  }
}
PKGEOF
    ok "Created $PKG_FILE"
fi

if command -v bun &>/dev/null; then
    (cd "$MCP_DIR" && bun install --no-save 2>/dev/null) && ok "Project plugins installed" || warn "bun install failed"
else
    warn "bun not found — run 'cd $MCP_DIR && npm install' manually"
fi

# ---------------------------------------------------------------------------
# 5. Global plugin check
# ---------------------------------------------------------------------------
if [ -f "$OPENCODE_CONFIG_DIR/opencode.json" ]; then
    ok "Global config exists at $OPENCODE_CONFIG_DIR/opencode.json"
else
    warn "No global config found. Run install.sh first for full plugin setup:"
    warn "  curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "==========================================="
ok "Project configured for opencode-crane!"
echo "==========================================="
echo ""
info "Start OpenCode and try:"
echo "  > help me init this repo as a research project"
echo ""
