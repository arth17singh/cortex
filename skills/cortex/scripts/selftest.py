#!/usr/bin/env python3
"""CORTEX self-test: pick recent decisions and rejections from session logs to quiz memory on.

usage: selftest.py <project_dir> [--all] [--max N]

Read-only. Prints JSON: the facts to turn into questions (each with its source file:line), and which
session logs changed since the last self-test recorded in memory/log/selftest.md. --all ignores that
date (for a manual /cortex selftest). The procedure that uses this is reference/selftest.md.
"""
import json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cortex_hook as h  # noqa: E402

SECTIONS = (('rejected', re.compile(r'^##\s+(alternatives\s+)?rejected', re.I)),
            ('decision', re.compile(r'^##\s+decisions', re.I)))


def facts_in(log, root):
    """[(kind, text, 'sessions/<file>:<line>')] from a log's decision and rejection sections."""
    out, kind = [], None
    for n, line in enumerate(log.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if line.startswith('#'):
            kind = next((k for k, rx in SECTIONS if rx.match(line)), None)
        elif kind and line.startswith('- ') and len(line) > 12 and not line[2:].lstrip().startswith('<'):
            text = re.sub(r'\s+', ' ', line[2:]).strip()
            out.append((kind, text[:400], f"{log.relative_to(root / 'memory').as_posix()}:{n}"))
    return out


def main():
    args = sys.argv[1:]
    root = h.find_root(next((a for a in args if not a.startswith('--') and not a.isdigit()), '.'))
    if not root:
        print(json.dumps({'error': 'no CORTEX memory here'}))
        return
    limit = int(args[args.index('--max') + 1]) if '--max' in args else 10
    since = 0.0 if '--all' in args else h.last_selftest(root)[0]
    logs = sorted((f for f in (root / 'memory' / 'sessions').glob('*.md')
                   if f.name not in h.MAPS and f.stat().st_mtime > since),
                  key=lambda f: f.stat().st_mtime, reverse=True)
    per_log = [sorted(facts_in(f, root), key=lambda x: x[0] != 'rejected') for f in logs]
    picked = []
    while len(picked) < limit and any(per_log):  # round-robin across logs, rejections first
        for facts in per_log:
            if facts and len(picked) < limit:
                picked.append(facts.pop(0))
    print(json.dumps({
        'project': str(root),
        'since': time.strftime('%Y-%m-%d %H:%M', time.localtime(since)) if since else None,
        'logs': [f.name for f in logs],
        'facts': [{'kind': k, 'text': t, 'source': s} for k, t, s in picked],
    }, indent=1))


if __name__ == '__main__':
    main()
