#!/usr/bin/env python3
"""Add or remove the CORTEX SessionStart/Stop hooks in a Claude Code settings.json.

usage: install_hooks.py <settings.json> <hook-script-path> [--remove]

Idempotent. Backs the file up first, appends to existing hook arrays without touching other
entries, and re-parses the result before reporting success.
"""
import json, shutil, sys, time
from pathlib import Path

EVENTS = {'SessionStart': 20, 'Stop': 10}
MARK = 'cortex_hook.py'


def has_cortex(group):
    return any(MARK in h.get('command', '') for h in group.get('hooks', []))


def main():
    args = [a for a in sys.argv[1:] if a != '--remove']
    remove = '--remove' in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    path, script = Path(args[0]).expanduser(), args[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text() or '{}') if path.exists() else {}
    hooks = data.setdefault('hooks', {})
    changed = False
    for event, timeout in EVENTS.items():
        groups = hooks.get(event, [])
        kept = [g for g in groups if not has_cortex(g)]
        if remove:
            changed |= len(kept) != len(groups)
            groups = kept
        elif len(kept) == len(groups):
            groups = groups + [{'hooks': [{'type': 'command', 'command': f'python3 "{script}"', 'timeout': timeout}]}]
            changed = True
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if not hooks:
        data.pop('hooks')
    if not changed:
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
