#!/usr/bin/env bash
# Install the CORTEX skill into Claude Code.
#   ./install.sh            copy into ~/.claude/skills/cortex
#   ./install.sh --link     symlink instead (edits here go live; `git pull` updates)
#   ./install.sh --project  install into ./.claude/skills/cortex of the current dir
#   ./install.sh --hooks    also register the hooks and the memory tools (no prompt)
#   ./install.sh --no-hooks skip the hooks (no prompt)
#   ./install.sh --uninstall-hooks   remove the hooks and the memory tools again
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/skills/cortex"
DEST_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
MODE=copy
HOOKS=ask
PROJECT=0
REMOVE=0
ROOT="$(cd "$(dirname "$0")" && pwd)"

for arg in "$@"; do
  case "$arg" in
    --link) MODE=link ;;
    --project) DEST_ROOT="$PWD/.claude/skills"; PROJECT=1 ;;
    --hooks) HOOKS=yes ;;
    --no-hooks) HOOKS=no ;;
    --uninstall-hooks) REMOVE=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 1 ;;
  esac
done

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }

DEST="$DEST_ROOT/cortex"
CONFIG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
if [ "$PROJECT" = 1 ]; then SETTINGS="$PWD/.claude/settings.json"; HOOK_SCRIPT='$CLAUDE_PROJECT_DIR/.claude/skills/cortex/scripts/cortex_hook.py'
else SETTINGS="$CONFIG/settings.json"; HOOK_SCRIPT="$DEST/scripts/cortex_hook.py"; fi
if [ "$REMOVE" = 1 ]; then
  python3 "$ROOT/hooks/install_hooks.py" "$SETTINGS" "$HOOK_SCRIPT" --remove
  if command -v claude >/dev/null; then claude mcp remove cortex >/dev/null 2>&1 && echo "memory tools removed"; fi
  exit 0
fi
mkdir -p "$DEST_ROOT"
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  # back up outside skills/, or Claude Code would load the backup as a second "cortex" skill
  mkdir -p "$DEST_ROOT/../cortex-backups"
  BACKUP="$(cd "$DEST_ROOT/.." && pwd)/cortex-backups/cortex.bak-$(date +%Y%m%d%H%M%S)"
  mv "$DEST" "$BACKUP"
  echo "existing install moved to $BACKUP"
fi

if [ "$MODE" = link ]; then ln -s "$SRC" "$DEST"; else cp -R "$SRC" "$DEST"; fi
echo "CORTEX installed at $DEST ($MODE)"
echo "Next: open Claude Code in a project and run /cortex help"

if [ "$HOOKS" = ask ]; then
  if [ -t 0 ]; then
    printf '\nRegister the CORTEX hooks in %s and the memory tools (MCP)? (recommended) [y/N] ' "$SETTINGS"
    read -r reply; case "$reply" in [yY]*) HOOKS=yes ;; *) HOOKS=no ;; esac
  else HOOKS=no; fi
fi
if [ "$HOOKS" = yes ]; then
  python3 "$ROOT/hooks/install_hooks.py" "$SETTINGS" "$HOOK_SCRIPT"
  if command -v claude >/dev/null; then
    if [ "$PROJECT" = 1 ]; then SCOPE=project; MCP_SCRIPT="$PWD/.claude/skills/cortex/scripts/cortex_mcp.py"
    else SCOPE=user; MCP_SCRIPT="$DEST/scripts/cortex_mcp.py"; fi
    claude mcp remove --scope "$SCOPE" cortex >/dev/null 2>&1
    if claude mcp add --scope "$SCOPE" cortex -- python3 "$MCP_SCRIPT" >/dev/null 2>&1; then
      echo "memory tools registered ($SCOPE scope): memory_search, memory_open, memory_timeline, memory_brief, memory_record"
    else
      echo "Could not register the memory tools; run: claude mcp add --scope $SCOPE cortex -- python3 $MCP_SCRIPT"
    fi
  else
    echo "claude CLI not found: register the memory tools later with: claude mcp add --scope user cortex -- python3 $DEST/scripts/cortex_mcp.py"
  fi
else
  echo "Hooks skipped. Add them later with: ./install.sh --hooks   (or /cortex config hooks=install)"
fi
