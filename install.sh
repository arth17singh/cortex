#!/usr/bin/env bash
# Install the CORTEX skill into Claude Code.
#   ./install.sh            copy into ~/.claude/skills/cortex
#   ./install.sh --link     symlink instead (edits here go live; `git pull` updates)
#   ./install.sh --project  install into ./.claude/skills/cortex of the current dir
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/skills/cortex"
DEST_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
MODE=copy

for arg in "$@"; do
  case "$arg" in
    --link) MODE=link ;;
    --project) DEST_ROOT="$PWD/.claude/skills" ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 1 ;;
  esac
done

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }

DEST="$DEST_ROOT/cortex"
mkdir -p "$DEST_ROOT"
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  BACKUP="$DEST.bak-$(date +%Y%m%d%H%M%S)"
  mv "$DEST" "$BACKUP"
  echo "existing install moved to $BACKUP"
fi

if [ "$MODE" = link ]; then ln -s "$SRC" "$DEST"; else cp -R "$SRC" "$DEST"; fi
echo "CORTEX installed at $DEST ($MODE)"
echo "Next: open Claude Code in a project and run /cortex help"
