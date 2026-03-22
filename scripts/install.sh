#!/usr/bin/env bash
# ============================================================================
# opencode-crane installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash
#
# Or manually:
#   git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
#   cd ~/.opencode-crane && bash scripts/install.sh
# ============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO_URL="https://github.com/AugustChaoTW/opencode-crane.git"
INSTALL_DIR="${CRANE_INSTALL_DIR:-$HOME/.opencode-crane}"
VENV_DIR="$INSTALL_DIR/.venv"
PYTHON="${CRANE_PYTHON:-python3}"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[crane]${NC} $*"; }
ok()    { echo -e "${GREEN}[crane]${NC} $*"; }
warn()  { echo -e "${YELLOW}[crane]${NC} $*"; }
err()   { echo -e "${RED}[crane]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
info "Checking prerequisites..."

if ! command -v "$PYTHON" &>/dev/null; then
    err "Python 3 not found. Install Python 3.10+ first."
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    err "Python $PY_VERSION detected. Requires Python 3.10+."
    exit 1
fi
ok "Python $PY_VERSION"

if ! command -v git &>/dev/null; then
    err "git not found. Install git first."
    exit 1
fi
ok "git $(git --version | awk '{print $3}')"

if ! command -v gh &>/dev/null; then
    warn "gh (GitHub CLI) not found. Task management tools won't work."
    warn "Install: https://cli.github.com/"
else
    if gh auth status &>/dev/null 2>&1; then
        ok "gh CLI authenticated"
    else
        warn "gh CLI found but not authenticated. Run: gh auth login"
    fi
fi

# ---------------------------------------------------------------------------
# Clone or update
# ---------------------------------------------------------------------------
if [ -d "$INSTALL_DIR/.git" ]; then
    info "Updating existing installation at $INSTALL_DIR..."
    git -C "$INSTALL_DIR" pull --ff-only 2>/dev/null || {
        warn "git pull failed, continuing with existing version"
    }
else
    info "Cloning opencode-crane to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# ---------------------------------------------------------------------------
# Create venv and install
# ---------------------------------------------------------------------------
info "Setting up Python virtual environment..."
"$PYTHON" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$INSTALL_DIR"
ok "Dependencies installed"

# ---------------------------------------------------------------------------
# Verify installation
# ---------------------------------------------------------------------------
info "Verifying installation..."
TOOL_COUNT=$("$VENV_DIR/bin/python" -c "
from crane.server import mcp
tools = mcp._tool_manager._tools if hasattr(mcp, '_tool_manager') else {}
print(len(tools))
" 2>/dev/null)

EXPECTED_TOOLS=23

if [ "$TOOL_COUNT" = "$EXPECTED_TOOLS" ]; then
    ok "MCP Server OK: $TOOL_COUNT tools registered"
else
    err "Expected $EXPECTED_TOOLS tools, got: ${TOOL_COUNT:-0}"
    exit 1
fi

# ---------------------------------------------------------------------------
# Print MCP config snippet
# ---------------------------------------------------------------------------
PYTHON_BIN="$VENV_DIR/bin/python"

echo ""
echo "==========================================="
ok "opencode-crane installed successfully!"
echo "==========================================="
echo ""
info "Next steps:"
echo ""
echo "  1. Add MCP config to your project's .opencode/opencode.json:"
echo ""
echo "     mkdir -p .opencode"
echo "     cat > .opencode/opencode.json << 'EOF'"
echo "     {"
echo "       \"mcp\": {"
echo "         \"crane\": {"
echo "           \"type\": \"local\","
echo "           \"command\": [\"$PYTHON_BIN\", \"-m\", \"crane\"],"
echo "           \"enabled\": true"
echo "         }"
echo "       }"
echo "     }"
echo "     EOF"
echo ""
echo "  2. (Optional) Install SKILL.md for AI guidance:"
echo ""
echo "     mkdir -p .opencode/skills/opencode-crane"
echo "     cp $INSTALL_DIR/SKILL.md .opencode/skills/opencode-crane/SKILL.md"
echo ""
echo "  3. Start OpenCode and try:"
echo "     > help me init this repo as a research project"
echo ""
