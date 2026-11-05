#!/usr/bin/env python3
"""Add or remove the CORTEX hooks in a Claude Code settings.json.

usage: install_hooks.py <settings.json> <path-to-cortex_hook.py> [--remove]

Installs the v8 set (all scripts live next to cortex_hook.py):
  SessionStart      cortex_hook.py     chat id, recording mode, catch-up brief, archive catch-up, re-anchor after compaction
  UserPromptSubmit  cortex_inject.py   relevant memory and other chats' news with each message
  PreToolUse        cortex_guard.py    protects script-owned files, adds provenance to writes
  PostToolUse       cortex_guard.py    lints memory edits
  Stop              cortex_hook.py     logging nudge
  Stop              cortex_capture.py  archives the chat and captures records in the background
Idempotent: an existing CORTEX entry for an event is replaced, other hooks are left alone. Backs the file up
first and re-parses the result before reporting success. Every hook is silent outside CORTEX projects, and the
v8-only ones stay silent in projects still on v5.
"""
import json, shutil, sys, time
from pathlib import PurePosixPath, Path

CORTEX_SCRIPTS = ('cortex_hook.py', 'cortex_inject.py', 'cortex_guard.py', 'cortex_capture.py')
PLAN = [  # (event, matcher or None, script, timeout)
    ('SessionStart', None, 'cortex_hook.py', 20),
    ('UserPromptSubmit', None, 'cortex_inject.py', 10),
    ('PreToolUse', 'Edit|Write|MultiEdit|Bash|Read|Grep|Glob|mcp__cortex__memory_record', 'cortex_guard.py', 5),
    ('PostToolUse', 'Edit|Write|MultiEdit|Bash', 'cortex_guard.py', 5),
    ('Stop', None, 'cortex_hook.py', 10),
    ('Stop', None, 'cortex_capture.py', 5),
]


def is_cortex(group):
    return any(any(s in h.get('command', '') for s in CORTEX_SCRIPTS) for h in group.get('hooks', []))


def main():
    args = [a for a in sys.argv[1:] if a != '--remove']
    remove = '--remove' in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    path = Path(args[0]).expanduser()
    scripts = str(PurePosixPath(args[1]).parent)        # may hold an unexpanded $CLAUDE_PROJECT_DIR: keep as text
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text() or '{}') if path.exists() else {}
    before = json.dumps(data, sort_keys=True)
    hooks = data.setdefault('hooks', {})
    for event in {e for e, _, _, _ in PLAN}:
        kept = [g for g in hooks.get(event, []) if not is_cortex(g)]
        if not remove:
            for e, matcher, script, timeout in PLAN:
                if e == event:
                    g = {'hooks': [{'type': 'command', 'command': f'python3 "{scripts}/{script}"', 'timeout': timeout}]}
                    if matcher:
                        g = {'matcher': matcher, **g}
                    kept.append(g)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if not hooks:
        data.pop('hooks')
    if json.dumps(data, sort_keys=True) == before:
        print(f'hooks already {"absent" if remove else "installed"} in {path}')
        return
    if path.exists():
        backup = path.with_name(f'{path.name}.bak-cortex-{time.strftime("%Y%m%d%H%M%S")}')
        shutil.copy2(path, backup)
        print(f'backup: {backup}')
    path.write_text(json.dumps(data, indent=2) + '\n')
    json.loads(path.read_text())
    print(f'hooks {"removed from" if remove else "installed in"} {path}')


main()
