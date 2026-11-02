#!/usr/bin/env python3
"""CORTEX hooks for Claude Code (SessionStart, Stop). Registered in settings.json.

SessionStart (startup, resume, clear, compact): prints a short CORTEX line into the chat's context:
  this chat's session id and transcript, the recording mode, this chat's ledger row, and gaps in
  other (non-active) chats that need recovering.
Stop: if this chat is recording and its ledger `live` end is far behind the transcript, it returns
  a non-blocking nudge (additionalContext) asking Claude to log what's worth keeping and bump the
  ledger. It never edits the ledger itself: only Claude may mark lines as covered, after it has
  actually logged them. Nudges are rate-limited per chat.

It is silent and exits 0 whenever the project has no CORTEX memory or anything goes wrong.
"""
import json, os, re, subprocess, sys, tempfile
from pathlib import Path

NUDGE_EVERY = 150      # transcript lines between nudges
MIN_UNTRACKED = 60     # an untracked chat must be at least this long before the first nudge
HERE = Path(__file__).resolve().parent


def find_root(cwd):
    p = Path(cwd or os.getcwd()).resolve()
    for d in [p, *p.parents]:
        if (d / 'memory' / 'LEDGER.md').is_file() and (d / 'memory' / 'INDEX.md').is_file():
            return d
    return None


def count_lines(path):
    n = 0
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            n += chunk.count(b'\n')
    return n


def recording_mode(root):
    for line in (root / 'memory' / 'INDEX.md').read_text(encoding='utf-8', errors='replace').splitlines():
        if line.lower().startswith('recording:'):
            return line.split(':', 1)[1].strip()
    return 'auto'


def ledger_row(root, session_id):
    """Return (state, ranges_text) for this chat, or (None, '')."""
    short = session_id[:8]
    for row in (root / 'memory' / 'LEDGER.md').read_text(encoding='utf-8', errors='replace').splitlines():
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        if len(cells) >= 4 and cells[0].strip('`').startswith(short):
            return cells[2].lower(), cells[3]
    return None, ''


def ranges(text):
    t = re.sub(r'\([^)]*\)', ' ', text.replace('`', '').replace('*', '')).replace('–', '-').replace('—', '-').lower()
    out, kind = [], None
    for part in re.split(r'[;,]', t):
        m = re.fullmatch(r'\s*(?:([a-z]+)\s+)?(\d+)\s*-\s*(\d*)\s*', part)
        if m:
            kind = m.group(1) or kind
            out.append((kind, int(m.group(2)), int(m.group(3)) if m.group(3) else None))
    return out


def session_start(data, root):
    sid, tp = data.get('session_id', ''), data.get('transcript_path', '')
    mode = recording_mode(root)
    state, rtext = ledger_row(root, sid)
    lines = [f"CORTEX: this chat is {sid[:8]} (session {sid}); transcript {tp}. Recording: {mode}."]
    lines.append(f"This chat's ledger row: {state} {rtext}." if state else "This chat has no ledger row yet.")
    try:
        out = subprocess.run([sys.executable, str(HERE / 'ledger_scan.py'), str(root), '--current', sid, '--json'],
                             capture_output=True, text=True, timeout=20)
        scan = json.loads(out.stdout)
        todo = [f"{c['short']} {', '.join(f'{a}-{b}' for a, b in c['backfill'])}" for c in scan.get('chats', [])
                if c.get('backfill') and 'live' in (c.get('ranges') or '')]
        untracked = [c['short'] for c in scan.get('chats', []) if c.get('state') == 'untracked' and c.get('backfill')]
        if todo:
            lines.append('Recover these unlogged tails before other work (CLAUDE.md §1): ' + '; '.join(todo) + '.')
        if untracked:
            lines.append(f"{len(untracked)} chat(s) were never tracked; suggest /cortex all if they matter.")
        if scan.get('warnings'):
            lines.append('Ledger warnings: ' + ' | '.join(scan['warnings'][:3]))
    except Exception:
        pass
    if data.get('source') == 'compact':
        lines.append("After compaction: keep appending to this chat's existing session log (listed in its ledger row).")
    print(' '.join(lines))


def stop(data, root):
    if data.get('stop_hook_active'):
        return
    sid, tp = data.get('session_id', ''), data.get('transcript_path', '')
    if not sid or not tp or not os.path.isfile(tp):
        return
    mode = recording_mode(root).lower()
    if mode.startswith('paused'):
        return
    state, rtext = ledger_row(root, sid)
    rs = ranges(rtext)
    if state == 'excluded' or any(k == 'paused' and b is None for k, a, b in rs):
        return
    live = [r for r in rs if r[0] in ('live', 'mined')]
    if mode.startswith('manual') and not any(k == 'live' for k, a, b in rs):
        return
    n = count_lines(tp)
    covered_to = max([b or a for k, a, b in live], default=0)
    if not live and n < MIN_UNTRACKED:
        return
    state_dir = Path(tempfile.gettempdir()) / 'cortex-hook'
    state_dir.mkdir(exist_ok=True)
    marker = state_dir / f'{sid}.json'
    last = json.loads(marker.read_text()).get('nudged_at', 0) if marker.exists() else 0
    if n - max(covered_to, last) < NUDGE_EVERY:
        return
    marker.write_text(json.dumps({'nudged_at': n}))
    if live:
        msg = (f"CORTEX: {n - covered_to} transcript lines since this chat's last memory update "
               f"(ledger live end {covered_to}, transcript now {n}). If anything since then passes the storage test, "
               f"append it to this chat's session log (and the matching L1 file), then set the ledger live end to {n}. "
               f"If nothing does, just set the ledger live end to {n}. Keep it brief, then stop.")
    else:
        msg = (f"CORTEX: this chat ({sid[:8]}) has no session log or ledger row yet, and recording is {mode}. "
               f"If anything so far passes the storage test, create the session log and the ledger row "
               f"(live 1-{n}) per CLAUDE.md §4. If nothing does, add the row as 'skipped 1-{n}'. Then stop.")
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'Stop', 'additionalContext': msg}}))


def main():
    try:
        data = json.loads(sys.stdin.read() or '{}')
        root = find_root(data.get('cwd'))
        if not root:
            return
        event = data.get('hook_event_name')
        if event == 'SessionStart':
            session_start(data, root)
        elif event == 'Stop':
            stop(data, root)
    except Exception:
        pass


if __name__ == '__main__':
    main()
    sys.exit(0)
