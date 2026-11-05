#!/usr/bin/env python3
"""CORTEX chat archive: a redacted, line-addressed copy of every recorded chat, kept in memory/chats/.

usage: cortex_archive.py --root DIR --all [--transcripts DIR] [--tz IANA]
       cortex_archive.py --root DIR --transcript PATH [--session ID] [--tz IANA]

Why: records and notes are summaries, and summaries drop details. The chat itself is the only complete account,
and Claude Code deletes transcripts after `cleanupPeriodDays` (30 by default). The archive keeps the readable
text of each chat (extract_transcript.py: user and assistant text, one line per tool call, subagent reports;
secrets and email addresses masked), with every block tagged `[L<n> ...]` by its line in the original transcript,
so search can point the agent at exact lines and `cortex_search.py --open <chat>:L<a>-<b>` can show them.

Rules it keeps:
- excluded chats (ledger) are never archived, and an existing archive of a chat excluded later is deleted;
- skipped and paused ranges (ledger) are never copied; nothing is copied while CORTEX is off for the chat;
- appends only what is new since the last run (per-chat state file, file-locked), so it is cheap on every Stop;
- memory/chats/.gitignore keeps the archive out of git unless the user decides otherwise.
"""
import argparse, fcntl, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cortex_lib as L  # noqa: E402

HEADER = ('# CORTEX chat archive · chat {chat} · redacted readable text; each block starts [L<n> date ROLE], '
          'n = line in the original transcript · script-owned, do not edit\n\n')


def chats_dir(root):
    d = Path(root) / 'memory' / 'chats'
    d.mkdir(parents=True, exist_ok=True)
    gi = d / '.gitignore'
    if not gi.exists():
        gi.write_text('# chat archives stay local unless you remove this file\n*\n!.gitignore\n')
    return d


def complete_lines(path):
    """Number of complete (newline-terminated) lines: a line still being written is left for the next run."""
    n = 0
    with open(path, 'rb') as f:
        for line in f:
            if line.endswith(b'\n'):
                n += 1
    return n


def tz_of(root):
    try:
        head = '\n'.join((Path(root) / 'memory' / 'INDEX.md').read_text(encoding='utf-8', errors='replace').splitlines()[:4])
    except OSError:
        return 'UTC'
    m = re.search(r'\b([A-Z][a-z]+/[A-Za-z_]+(?:/[A-Za-z_]+)?)\b', head)
    return m.group(1) if m else 'UTC'


def chat_off(root, chat):
    """CORTEX off for the project or for this chat (ledger Notes)."""
    try:
        import cortex_hook as H
        return H.memory_switch(Path(root), chat)[0] == 'off'
    except Exception:
        return False


def archive_one(root, path, tz, state='', ranges=''):
    """Append the new part of one transcript to memory/chats/<chat>.txt. Returns the number of blocks added."""
    path = Path(path)
    chat = path.stem[:8]
    d = chats_dir(root)
    out, st_path = d / f'{chat}.txt', d / f'.{chat}.state'
    if state == 'excluded':
        for p in (out, st_path):
            if p.exists():
                p.unlink()
        return 0
    if not path.is_file() or chat_off(root, chat):
        return 0
    with open(st_path, 'a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        lock.seek(0)
        try:
            last = int((lock.read() or '0').strip() or 0)
        except ValueError:
            last = 0
        n = complete_lines(path)
        if n <= last:
            return 0
        text = subprocess.run([sys.executable, str(HERE / 'extract_transcript.py'), str(path), tz, str(last + 1), str(n)],
                              capture_output=True, text=True).stdout
        blocked = L.blocked_ranges(ranges, n)
        blocks = []
        for b in re.split(r'\n(?=\[L\d+ )', text):
            m = re.match(r'\[L(\d+) ', b)
            if m and not any(a <= int(m.group(1)) <= z for a, z in blocked):
                blocks.append(b.rstrip() + '\n')
        if blocks:
            new = not out.exists()
            with open(out, 'a', encoding='utf-8') as f:
                if new:
                    f.write(HEADER.format(chat=chat))
                f.write('\n'.join(blocks) + '\n')
        lock.seek(0)
        lock.truncate()
        lock.write(str(n))
        return len(blocks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--transcript')
    ap.add_argument('--session')
    ap.add_argument('--transcripts')
    ap.add_argument('--tz')
    a = ap.parse_args()
    root = L.find_root(a.root, explicit=True)
    if not root:
        sys.exit('no CORTEX memory here')
    tz = a.tz or tz_of(root)
    scan_args = [sys.executable, str(HERE / 'ledger_scan.py'), str(root), '--json']
    if a.transcripts:
        scan_args += ['--transcripts', a.transcripts]
    try:
        scan = json.loads(subprocess.run(scan_args, capture_output=True, text=True, timeout=60).stdout or '{}')
    except (ValueError, subprocess.TimeoutExpired):
        scan = {}
    chats = {c['short']: c for c in scan.get('chats', [])}
    done = {}
    if a.all:
        tdir = Path(scan.get('transcripts') or a.transcripts or '.')
        for short, c in chats.items():
            done[short] = archive_one(root, tdir / (c['id'] + '.jsonl'), tz, c['state'], c.get('ranges') or '')
    elif a.transcript:
        c = chats.get(Path(a.transcript).stem[:8], {})
        done[Path(a.transcript).stem[:8]] = archive_one(root, a.transcript, tz, c.get('state', ''), c.get('ranges') or '')
    print(json.dumps({'archived_blocks': done}))


if __name__ == '__main__':
    main()
