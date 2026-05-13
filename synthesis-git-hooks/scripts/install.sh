#!/bin/bash
#
# synthesis-git-hooks installer.
#
# Idempotent. Run multiple times safely. Copies the engine to
# ~/.synthesis/git-hooks/, sets git's `core.hooksPath`, and seeds an
# initial ~/.synthesis/git-hook-config.yaml from the bundled template
# (only if no config exists yet — does not overwrite existing config).
#
# Usage:
#   ~/.claude/skills/synthesis-git-hooks/scripts/install.sh
#
# Or directly from the skill's source:
#   ~/workspaces/<you>/synthesis-skills/synthesis-git-hooks/scripts/install.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

TARGET_DIR="$HOME/.synthesis/git-hooks"
CONFIG_PATH="$HOME/.synthesis/git-hook-config.yaml"

mkdir -p "$TARGET_DIR"
mkdir -p "$(dirname "$CONFIG_PATH")"

echo "→ Copying engine to $TARGET_DIR/"
cp -f "$SCRIPT_DIR/pre-commit" "$TARGET_DIR/pre-commit"
cp -f "$SCRIPT_DIR/_load_config.py" "$TARGET_DIR/_load_config.py"
chmod +x "$TARGET_DIR/pre-commit" "$TARGET_DIR/_load_config.py"

if [ -f "$CONFIG_PATH" ]; then
    echo "→ Config already exists at $CONFIG_PATH — not overwriting."
    echo "  (Edit it manually; the template is at $SCRIPT_DIR/git-hook-config.example.yaml.)"
else
    echo "→ Seeding initial config at $CONFIG_PATH from template"
    cp "$SCRIPT_DIR/git-hook-config.example.yaml" "$CONFIG_PATH"
    echo ""
    echo "  ⚠️  Edit $CONFIG_PATH and replace 'YOUR-PERSONAL-ORG' in"
    echo "      'personal_remote_patterns' with your actual GitHub user/org."
    echo ""
fi

CURRENT=$(git config --global core.hooksPath 2>/dev/null || true)
if [ "$CURRENT" = "$TARGET_DIR" ]; then
    echo "→ core.hooksPath already points to $TARGET_DIR"
else
    if [ -n "$CURRENT" ]; then
        echo "→ Current core.hooksPath: $CURRENT"
        echo "  Updating to: $TARGET_DIR"
    else
        echo "→ Setting core.hooksPath to: $TARGET_DIR"
    fi
    git config --global core.hooksPath "$TARGET_DIR"
fi

# Verify Python + PyYAML available
if ! python3 -c 'import yaml' 2>/dev/null; then
    echo ""
    echo "⚠️  PyYAML not installed. The sidecar needs it."
    echo "   Install with: pip3 install --user PyYAML"
fi

echo ""
echo "✓ synthesis-git-hooks installed."
echo ""
echo "  Engine:  $TARGET_DIR/pre-commit"
echo "  Sidecar: $TARGET_DIR/_load_config.py"
echo "  Config:  $CONFIG_PATH"
echo ""
echo "  Verify a repo's classification:"
echo "    cd <repo> && $TARGET_DIR/_load_config.py --classify"
echo ""
