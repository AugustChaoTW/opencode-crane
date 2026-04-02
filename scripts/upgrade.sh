#!/usr/bin/env bash
set -euo pipefail

CRANE_DIR="${CRANE_DIR:-$HOME/.opencode-crane}"
BACKUP_DIR="$CRANE_DIR/backups"
TARGET="${1:-latest}"
BACKUP="${BACKUP:-true}"
VERIFY="${VERIFY:-true}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "CRANE Upgrade Script"
echo "==================="
echo "Directory: $CRANE_DIR"
echo "Target: $TARGET"
echo ""

cd "$CRANE_DIR"

CURRENT=$(grep '^version' pyproject.toml | sed 's/.*"\(.*\)"/\1/')
echo "Current version: $CURRENT"

if [ "$BACKUP" = "true" ]; then
    echo "Creating backup..."
    mkdir -p "$BACKUP_DIR"
    BACKUP_PATH="$BACKUP_DIR/crane_$TIMESTAMP"
    mkdir -p "$BACKUP_PATH"
    for subdir in src data scripts pyproject.toml; do
        if [ -e "$subdir" ]; then
            cp -r "$subdir" "$BACKUP_PATH/"
        fi
    done
    echo "Backup saved to: $BACKUP_PATH"
fi

echo "Fetching latest..."
git fetch origin

if [ "$TARGET" = "latest" ]; then
    git pull origin main
else
    git checkout "v$TARGET"
fi

echo "Updating dependencies..."
uv sync

MIGRATION_SCRIPT="scripts/migrations/${TARGET}.py"
if [ -f "$MIGRATION_SCRIPT" ]; then
    echo "Running migration: $MIGRATION_SCRIPT"
    uv run python "$MIGRATION_SCRIPT"
fi

if [ "$VERIFY" = "true" ]; then
    echo "Running verification tests..."
    if uv run pytest tests/services/test_version_check_service.py -q --tb=no; then
        echo "Verification passed"
    else
        echo "WARNING: Some tests failed. Run 'bash scripts/rollback.sh' to rollback."
    fi
fi

NEW_VERSION=$(grep '^version' pyproject.toml | sed 's/.*"\(.*\)"/\1/')
echo ""
echo "Upgrade complete: $CURRENT → $NEW_VERSION"
