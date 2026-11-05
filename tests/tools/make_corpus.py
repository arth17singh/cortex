#!/usr/bin/env python3
"""Turn a folder of Claude Code transcripts into a CORTEX test project (no model calls).

usage: make_corpus.py <project dir> <transcripts dir> "<title>" [--tz IANA] [--code DIR]

Creates <project>/CLAUDE.md, memory/INDEX.md (minimal: no curated notes exist for these corpora),
memory/LEDGER.md (every chat recorded as `mined 1-<n>`), then the chat archive (memory/chats/) and the search
index (memory/.cache/). With --code, the repository code is copied in next to memory/ so arms can read it.
"""
import argparse, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / 'skills' / 'cortex' / 'scripts'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('transcripts')
    ap.add_argument('title')
    ap.add_argument('--tz', default='UTC')
    ap.add_argument('--code')
    a = ap.parse_args()
    p, tr = Path(a.project), Path(a.transcripts).resolve()
    if p.exists():
        shutil.rmtree(p)
    if a.code:
        shutil.copytree(a.code, p, symlinks=True, ignore=shutil.ignore_patterns('.git', 'node_modules', '.specstory'))
    (p / 'memory').mkdir(parents=True, exist_ok=True)
    (p / 'CLAUDE.md').write_text(f'# {a.title}\n\n<!-- CORTEX:BEGIN v5 -->\n<!-- CORTEX:END -->\n', encoding='utf-8')
    (p / 'memory' / 'INDEX.md').write_text(
        f'# Project memory: index\nLast updated: 2026-11-04 · Recording: auto · TZ: {a.tz}\n\n## Where we are\n'
        '- No curated notes for this project: memory is the chat archive and the records drawn from it.\n', encoding='utf-8')
    rows = []
    for f in sorted(tr.glob('*.jsonl')):
        n = sum(1 for line in open(f, 'rb') if line.endswith(b'\n'))
        rows.append(f'| `{f.stem}` | - | mined | mined 1-{n} | - | test corpus |')
    (p / 'memory' / 'LEDGER.md').write_text(
        '# CORTEX ledger: what has been tracked\n\n| Chat | Dates (local) | State | Ranges | Session logs | Notes |\n'
        '|---|---|---|---|---|---|\n' + '\n'.join(rows) + '\n', encoding='utf-8')
    r = subprocess.run([sys.executable, str(SCRIPTS / 'cortex_archive.py'), '--root', str(p), '--all', '--index',
                        '--transcripts', str(tr), '--tz', a.tz], capture_output=True, text=True)
    print(r.stdout.strip()[-400:] or r.stderr[-400:])
    chats = list((p / 'memory' / 'chats').glob('*.txt'))
    print(f'{p}: {len(rows)} chats in ledger, {len(chats)} archived, '
          f'{sum(c.stat().st_size for c in chats) / 1e6:.2f} MB archive')


if __name__ == '__main__':
    main()
