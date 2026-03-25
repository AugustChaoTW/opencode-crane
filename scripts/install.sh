#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/AugustChaoTW/opencode-crane.git"
INSTALL_DIR="${CRANE_INSTALL_DIR:-$HOME/.opencode-crane}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[crane]${NC} $*"; }
ok()    { echo -e "${GREEN}[crane]${NC} $*"; }
warn()  { echo -e "${YELLOW}[crane]${NC} $*"; }
err()   { echo -e "${RED}[crane]${NC} $*" >&2; }

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "${ID:-unknown}"
    else
        echo "unknown"
    fi
}

detect_package_manager() {
    if command -v apt-get &>/dev/null; then
        echo "apt"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v yum &>/dev/null; then
        echo "yum"
    else
        echo "unknown"
    fi
}

install_system_deps() {
    local pkg_mgr="$1"
    local deps=()

    if ! command -v git &>/dev/null; then deps+=("git"); fi
    if ! command -v curl &>/dev/null; then deps+=("curl"); fi

    [ ${#deps[@]} -eq 0 ] && return 0

    info "Installing system dependencies: ${deps[*]}"

    case "$pkg_mgr" in
        apt)  sudo apt-get update -qq && sudo apt-get install -y -qq "${deps[@]}" ;;
        dnf)  sudo dnf install -y -q "${deps[@]}" ;;
        yum)  sudo yum install -y -q "${deps[@]}" ;;
        *)    err "Cannot install automatically. Please install: ${deps[*]}"; exit 1 ;;
    esac

    ok "System dependencies installed"
}

install_uv() {
    if command -v uv &>/dev/null; then
        ok "uv $(uv --version | awk '{print $2}')"
        return 0
    fi

    info "Installing uv (fast Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"

    if command -v uv &>/dev/null; then
        ok "uv $(uv --version | awk '{print $2}')"
    else
        err "Failed to install uv. Install manually: https://docs.astral.sh/uv/"
        exit 1
    fi
}

install_gh() {
    if command -v gh &>/dev/null; then
        gh auth status &>/dev/null 2>&1 && ok "gh CLI authenticated" || warn "gh CLI found but not authenticated. Run: gh auth login"
        return 0
    fi

    local pkg_mgr="$1"
    info "Installing GitHub CLI..."

    case "$pkg_mgr" in
        apt)
            local gh_version
            gh_version=$(curl -s https://api.github.com/repos/cli/cli/releases/latest | grep -oP '"tag_name": "v\K[^"]*')
            curl -sL "https://github.com/cli/cli/releases/download/v${gh_version}/gh_${gh_version}_linux_amd64.deb" -o /tmp/gh.deb
            sudo dpkg -i /tmp/gh.deb
            rm -f /tmp/gh.deb
            ;;
        dnf|yum)
            sudo dnf install -y 'dnf-command(config-manager)' 2>/dev/null || true
            sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo 2>/dev/null || true
            sudo "$pkg_mgr" install -y gh
            ;;
        *)  warn "Cannot install gh automatically. Install manually: https://cli.github.com/" ; return 0 ;;
    esac

    command -v gh &>/dev/null && ok "gh $(gh --version | head -1 | awk '{print $3}')" || warn "Failed to install gh"
}

info "Checking prerequisites..."

OS_ID=$(detect_os)
PKG_MGR=$(detect_package_manager)
info "Detected OS: $OS_ID (package manager: $PKG_MGR)"

install_system_deps "$PKG_MGR"

if ! command -v git &>/dev/null; then err "git not found"; exit 1; fi
ok "git $(git --version | awk '{print $3}')"

install_uv
install_gh "$PKG_MGR"

if [ -d "$INSTALL_DIR/.git" ]; then
    info "Updating existing installation at $INSTALL_DIR..."
    git -C "$INSTALL_DIR" pull --ff-only 2>/dev/null || warn "git pull failed, continuing with existing version"
else
    info "Cloning opencode-crane to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

info "Installing opencode-crane with uv..."
cd "$INSTALL_DIR"
uv sync --quiet
ok "Dependencies installed"

info "Verifying installation..."
TOOL_COUNT=$(uv run python -c "
from crane.server import mcp
tools = mcp._tool_manager._tools if hasattr(mcp, '_tool_manager') else {}
print(len(tools))
" 2>/dev/null)

EXPECTED_TOOLS=34
if [ "$TOOL_COUNT" = "$EXPECTED_TOOLS" ]; then
    ok "MCP Server OK: $TOOL_COUNT tools registered"
else
    warn "Expected $EXPECTED_TOOLS tools, got: ${TOOL_COUNT:-0}"
fi

echo ""
echo "==========================================="
ok "opencode-crane installed successfully!"
echo "==========================================="
echo ""
info "Installation details:"
echo "  - Install dir: $INSTALL_DIR"
echo "  - Python: $(uv python find 2>/dev/null || echo 'uv managed')"
echo "  - uv: $(uv --version | awk '{print $2}')"
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
echo "           \"command\": [\"sh\", \"-c\", \"cd $INSTALL_DIR && uv run crane\"],"
echo "           \"enabled\": true"
echo "         }"
echo "       }"
echo "     }"
echo "     EOF"
echo ""
echo "     Or use the global config:"
echo ""
echo "     mkdir -p ~/.config/opencode"
echo "     cat > ~/.config/opencode/opencode.json << 'EOF'"
echo "     {"
echo "       \"\$schema\": \"https://opencode.ai/config.json\","
echo "       \"mcp\": {"
echo "         \"crane\": {"
echo "           \"type\": \"local\","
echo "           \"command\": [\"sh\", \"-c\", \"cd $INSTALL_DIR && uv run crane\"],"
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
echo "  3. (Optional) Authenticate GitHub CLI:"
echo ""
echo "     gh auth login"
echo ""
echo "  4. Start OpenCode and try:"
echo "     > help me init this repo as a research project"
echo ""
