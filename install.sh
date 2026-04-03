#!/bin/bash
set -e

REPO="incadawr/skill.taskana-tasks"
CLI_DEST="$HOME/.local/bin/taskana-cli"
SKILL_DIR="$HOME/.claude/skills/taskana-tasks"

echo "Installing skill.taskana-tasks..."

# CLI
mkdir -p "$(dirname "$CLI_DEST")"
curl -fsSL "https://raw.githubusercontent.com/$REPO/main/cli/taskana_cli.py" -o "$CLI_DEST"
chmod +x "$CLI_DEST"
echo "  CLI installed: $CLI_DEST"

# Skill
mkdir -p "$SKILL_DIR"
curl -fsSL "https://raw.githubusercontent.com/$REPO/main/skill/taskana-tasks.md" -o "$SKILL_DIR/SKILL.md"
echo "  Skill installed: $SKILL_DIR/SKILL.md"

# Check PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo ""
    echo "NOTE: Add ~/.local/bin to your PATH:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
fi

echo ""
echo "Done! Run 'taskana-cli --version' to verify."
