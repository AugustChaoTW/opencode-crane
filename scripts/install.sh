#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/AugustChaoTW/opencode-crane.git"
INSTALL_DIR="${CRANE_INSTALL_DIR:-$HOME/.opencode-crane}"
OPENCODE_CONFIG_DIR="$HOME/.config/opencode"

# Plugin sources
CLAUDE_MAX_HEADERS_URL="https://raw.githubusercontent.com/rynfar/opencode-claude-max-proxy/main/src/plugin/claude-max-headers.ts"
MEMORY_SYSTEM_REPO="https://github.com/AugustChaoTW/aug-money.git"

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

install_bun() {
    if command -v bun &>/dev/null; then
        ok "bun $(bun --version)"
        return 0
    fi

    info "Installing bun (JavaScript runtime for plugins)..."
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"

    if command -v bun &>/dev/null; then
        ok "bun $(bun --version)"
    else
        err "Failed to install bun. Install manually: https://bun.sh/"
        err "Plugins will not be installed."
        return 1
    fi
}

install_plugins() {
    info "Installing OpenCode plugins..."
    mkdir -p "$OPENCODE_CONFIG_DIR/plugins"

    local pkg_json="$OPENCODE_CONFIG_DIR/package.json"
    if [ ! -f "$pkg_json" ]; then
        cat > "$pkg_json" << 'PKGEOF'
{
  "dependencies": {
    "@opencode-ai/plugin": "^1.3.2",
    "oh-my-opencode": "^3.12.3",
    "opencode-claude-auth": "^1.3.1"
  }
}
PKGEOF
        ok "Created $pkg_json"
    else
        local changed=false
        for pkg in oh-my-opencode opencode-claude-auth; do
            if ! grep -q "\"$pkg\"" "$pkg_json"; then
                warn "$pkg not found in $pkg_json — add it manually"
                changed=true
            fi
        done
        $changed || ok "package.json already has required plugins"
    fi

    info "Installing npm plugins via bun..."
    (cd "$OPENCODE_CONFIG_DIR" && bun install --no-save 2>/dev/null) && ok "npm plugins installed" || warn "bun install failed"

    local headers_dir="$OPENCODE_CONFIG_DIR/plugins/claude-max-headers"
    if [ -f "$headers_dir/claude-max-headers.ts" ]; then
        ok "claude-max-headers already installed"
    else
        info "Downloading claude-max-headers plugin..."
        mkdir -p "$headers_dir"
        if curl -fsSL "$CLAUDE_MAX_HEADERS_URL" -o "$headers_dir/claude-max-headers.ts"; then
            ok "claude-max-headers downloaded"
        else
            warn "Failed to download claude-max-headers"
        fi
    fi

    local memory_dir="$OPENCODE_CONFIG_DIR/plugins/memory-system"
    if [ -f "$memory_dir/index.js" ]; then
        ok "memory-system already installed"
    else
        info "Installing memory-system plugin..."
        local tmp_dir="/tmp/aug-money-$$"
        if git clone --depth 1 "$MEMORY_SYSTEM_REPO" "$tmp_dir" 2>/dev/null; then
            local src_dir="$tmp_dir/opencode-memory-system"
            if [ -d "$src_dir" ]; then
                mkdir -p "$memory_dir"
                (cd "$src_dir" && bun install --no-save 2>/dev/null && bun run build 2>/dev/null) || true
                if [ -f "$src_dir/dist/index.js" ]; then
                    cp "$src_dir/dist/index.js" "$memory_dir/index.js"
                    cp "$src_dir/package.json" "$memory_dir/package.json"
                    [ -f "$src_dir/dist/sql-wasm.wasm" ] && cp "$src_dir/dist/sql-wasm.wasm" "$memory_dir/sql-wasm.wasm"
                    ok "memory-system built and installed"
                else
                    warn "memory-system build failed — copy source for manual build"
                    cp -r "$src_dir"/* "$memory_dir/" 2>/dev/null || true
                fi
            else
                warn "memory-system source not found in repo"
            fi
            rm -rf "$tmp_dir"
        else
            warn "Failed to clone memory-system repo"
        fi
    fi
}

setup_plugin_config() {
    info "Configuring OpenCode plugins..."

    local config_file="$OPENCODE_CONFIG_DIR/opencode.json"
    if [ -f "$config_file" ]; then
        if grep -q '"plugin"' "$config_file"; then
            ok "opencode.json already has plugin config"
        else
            warn "opencode.json exists but no plugin[] — add manually:"
            echo '  "plugin": ["oh-my-opencode", "opencode-claude-auth", "./plugins/claude-max-headers/claude-max-headers.ts", "./plugins/memory-system"]'
        fi
    else
        mkdir -p "$OPENCODE_CONFIG_DIR"
        cat > "$config_file" << CFGEOF
{
  "\$schema": "https://opencode.ai/config.json",
  "plugin": [
    "oh-my-opencode",
    "opencode-claude-auth",
    "./plugins/claude-max-headers/claude-max-headers.ts",
    "./plugins/memory-system"
  ],
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["sh", "-c", "cd $INSTALL_DIR && uv run crane"],
      "enabled": true
    }
  }
}
CFGEOF
        ok "Created $config_file with plugins + crane MCP"
    fi

    local omo_config="$OPENCODE_CONFIG_DIR/oh-my-opencode.json"
    if [ -f "$omo_config" ]; then
        ok "oh-my-opencode.json already exists"
    else
        cat > "$omo_config" << 'OMOEOF'
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json",
  "google_auth": false,
  "agents": {}
}
OMOEOF
        ok "Created oh-my-opencode.json"
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
install_bun || true
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

# ---------------------------------------------------------------------------
# Plugins
# ---------------------------------------------------------------------------
if command -v bun &>/dev/null; then
    install_plugins
    setup_plugin_config
else
    warn "bun not available — skipping plugin installation"
    warn "Install bun manually (https://bun.sh/) then re-run this script"
fi

# ---------------------------------------------------------------------------
# SKILL.md
# ---------------------------------------------------------------------------
SKILL_DIR="$OPENCODE_CONFIG_DIR/skills/opencode-crane"
if [ -f "$SKILL_DIR/SKILL.md" ]; then
    ok "SKILL.md already installed"
else
    mkdir -p "$SKILL_DIR"
    cp "$INSTALL_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
    ok "Installed SKILL.md → $SKILL_DIR/SKILL.md"
fi

echo ""
echo "==========================================="
ok "opencode-crane installed successfully!"
echo "==========================================="
echo ""
info "Installation details:"
echo "  - CRANE:   $INSTALL_DIR"
echo "  - Config:  $OPENCODE_CONFIG_DIR"
echo "  - Python:  $(uv python find 2>/dev/null || echo 'uv managed')"
echo "  - uv:      $(uv --version | awk '{print $2}')"
if command -v bun &>/dev/null; then
echo "  - bun:     $(bun --version)"
fi
echo ""
info "Plugins installed:"
[ -d "$OPENCODE_CONFIG_DIR/node_modules/oh-my-opencode" ] && echo "  ✓ oh-my-opencode" || echo "  ✗ oh-my-opencode"
[ -d "$OPENCODE_CONFIG_DIR/node_modules/opencode-claude-auth" ] && echo "  ✓ opencode-claude-auth" || echo "  ✗ opencode-claude-auth"
[ -f "$OPENCODE_CONFIG_DIR/plugins/claude-max-headers/claude-max-headers.ts" ] && echo "  ✓ claude-max-headers" || echo "  ✗ claude-max-headers"
[ -f "$OPENCODE_CONFIG_DIR/plugins/memory-system/index.js" ] && echo "  ✓ memory-system" || echo "  ✗ memory-system"
echo ""
info "Next steps:"
echo ""
echo "  1. (Optional) Authenticate GitHub CLI:"
echo ""
echo "     gh auth login"
echo ""
echo "  2. Start OpenCode and try:"
echo "     > help me init this repo as a research project"
echo ""
