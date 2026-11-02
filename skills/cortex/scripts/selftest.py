#!/usr/bin/env python3
"""CORTEX self-test: pick facts from session logs to quiz memory on.

Most come from logs changed since the last self-test (rejections first, then decisions and findings);
two always come from the oldest logs, so old and subtle material keeps being tested too.

usage: selftest.py <project_dir> [--all] [--max N]

Read-only. Prints JSON: the facts to turn into questions (each with its source file:line), and which
session logs changed since the last self-test recorded in memory/log/selftest.md. --all ignores that
date (for a manual /cortex selftest). The procedure that uses this is reference/selftest.md.
"""
import json, random, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cortex_hook as h  # noqa: E402

SECTIONS = (('rejected', re.compile(r'^##\s+(alternatives\s+)?rejected', re.I)),
            ('decision', re.compile(r'^##\s+decisions', re.I)),
            ('finding', re.compile(r'^##\s+(key\s+)?findings|^##\s+verified', re.I)))
QA = re.compile(r'^##\s+\d+\.\s+"(.+?)"')  # Q&A logs: '## 3. "what is dp sgd" (date)'
OLD_PICKS = 2


def facts_in(log, root):
    """[(kind, text, 'sessions/<file>:<line>')]: rejections, decisions, findings and the user's Q&A questions."""
    out, kind = [], None
    for n, line in enumerate(log.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        qa = QA.match(line)
        if qa:  # the user's own question; its answer follows in the log
            out.append(('question', qa.group(1)[:400], f"{log.relative_to(root / 'memory').as_posix()}:{n}"))
            kind = None
        elif line.startswith('#'):
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
    order = {'rejected': 0, 'decision': 1, 'finding': 2, 'question': 3}
    per_log = [sorted(facts_in(f, root), key=lambda x: order[x[0]]) for f in logs]
    picked = []
    while len(picked) < limit - OLD_PICKS and any(per_log):  # round-robin across logs, rejections first
        for facts in per_log:
            if facts and len(picked) < limit - OLD_PICKS:
                picked.append(facts.pop(0))
    oldest = sorted((f for f in (root / 'memory' / 'sessions').glob('*.md') if f.name not in h.MAPS),
                    key=lambda f: f.name)  # names start with the date
    seen = {s for _, _, s in picked}
    pool = [x for f in oldest[:3] for x in facts_in(f, root) if x[2] not in seen]
    random.seed(time.strftime('%Y-%m-%d'))  # varies day to day, stable within a day
    picked += random.sample(pool, min(OLD_PICKS, len(pool)))
    print(json.dumps({
        'project': str(root),
        'since': time.strftime('%Y-%m-%d %H:%M', time.localtime(since)) if since else None,
        'logs': [f.name for f in logs],
        'facts': [{'kind': k, 'text': t, 'source': s} for k, t, s in picked],
    }, indent=1))


if __name__ == '__main__':
    main()
