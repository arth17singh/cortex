#!/usr/bin/env python3
"""Check CORTEX consolidation guarantees between a before and an after copy of a project.

usage: guarantees.py <before_dir> <after_dir>

1. Every per-log map line (index + sessions/README.md) still exists verbatim in the after maps.
2. Every per-file map line (index + _index.md files) still exists verbatim in the after maps.
3. Every distinctive noun of the before maps is still somewhere in the after maps.
4. The "open:" bullet and the "never" preference are still in L0 (index / preferences).
5. No session log or topic file was deleted.
"""
import re, sys
from pathlib import Path


def maps(root):
    mem = root / 'memory'
    files = [mem / 'INDEX.md', mem / 'sessions' / 'README.md', *mem.glob('*/_index.md')]
    return '\n'.join(f.read_text() for f in files if f.is_file())


def lines(root, pattern):
    return {l.strip() for l in maps(root).splitlines() if re.match(pattern, l.strip())}


before, after = Path(sys.argv[1]), Path(sys.argv[2])
after_maps = maps(after)
fails = []
log_lines = lines(before, r'^- `\d{4}-\d{2}-\d{2}_')
fails += [f'per-log line lost: {l[:90]}' for l in log_lines if l not in after_maps]
file_lines = {l for l in maps(before).splitlines() if re.match(r'^- [a-z0-9-]+: ', l)}
fails += [f'per-file line lost: {l[:90]}' for l in file_lines if l.strip() not in after_maps]
nouns = set(re.findall(r'[A-Za-z][A-Za-z0-9@/+.-]{3,}', maps(before)))
lost = sorted(n for n in nouns if n not in after_maps)
fails += [f'noun gone from all maps: {n}' for n in lost]
l0 = (after / 'memory' / 'INDEX.md').read_text() + (after / 'memory' / 'team' / 'user-preferences.md').read_text()
for must in ('open: decide the retention period for raw events', 'Never commit `memory/`'):
    if must not in l0:
        fails.append(f'left L0: {must}')
for kind in ('sessions/*.md', '*/*.md'):
    b = {p.relative_to(before) for p in (before / 'memory').glob(kind)}
    a = {p.relative_to(after) for p in (after / 'memory').glob(kind)}
    fails += [f'file deleted: {p}' for p in sorted(b - a)]
print(f'checked {len(log_lines)} per-log lines, {len(file_lines)} per-file lines, {len(nouns)} nouns')
print('PASS: no information left the maps' if not fails else f'FAIL ({len(fails)}):\n  ' + '\n  '.join(fails[:25]))
