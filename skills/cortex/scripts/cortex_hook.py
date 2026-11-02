#!/usr/bin/env python3
"""CORTEX hooks for Claude Code (SessionStart, Stop). Registered in settings.json.

SessionStart (startup, resume, clear, compact): prints a short CORTEX line into the chat's context:
  this chat's session id and transcript, the recording mode, this chat's ledger row, and gaps in
  other (non-active) chats that need recovering.
Stop: if this chat is recording and its ledger `live` end is far behind the transcript, it returns
  a non-blocking nudge (additionalContext) asking Claude to log what's worth keeping and bump the
  ledger. It never edits the ledger itself: only Claude may mark lines as covered, after it has
  actually logged them. Nudges are rate-limited per chat.

Both events also emit a `systemMessage` the user sees in their terminal: a one-line status at SessionStart,
and at Stop a 'synced' pulse (what changed in memory this turn, from file snapshots), any checkpoint nudge,
and a context gauge (how much memory is in this chat's context, from the transcript's Read calls and usage)
(put `Logs: off` anywhere in memory/INDEX.md, or set CORTEX_QUIET=1, to silence it).

It is silent and exits 0 whenever the project has no CORTEX memory or anything goes wrong.
"""
import json, os, re, subprocess, sys, tempfile, time
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


def logs_enabled(root):
    if os.environ.get('CORTEX_QUIET'):
        return False
    for line in (root / 'memory' / 'INDEX.md').read_text(encoding='utf-8', errors='replace').splitlines():
        if re.search(r'\blogs:\s*off\b', line, re.I):
            return False
    return True


def memory_stats(root):
    """Cheap filesystem facts for the telemetry panel: (l0_tokens, l1_files, l2_sessions)."""
    mem = root / 'memory'
    l0 = sum(f.stat().st_size for f in (mem / 'INDEX.md', mem / 'team' / 'user-preferences.md') if f.is_file())
    skip = {'sessions', 'log', '_templates', 'team'}
    l1 = [f for d in mem.iterdir() if d.is_dir() and d.name not in skip and not d.name.startswith('.')
          for f in d.glob('*.md')]
    return l0 // 4, len(l1), len(list((mem / 'sessions').glob('*.md')))


STATE_DIR = Path(tempfile.gettempdir()) / 'cortex-hook'
LAYER_SKIP = ('.migrated', '_templates')


def snapshot(root):
    """{relative path: line count} for every memory file; the basis for the live 'synced' pulse."""
    snap = {}
    for f in (root / 'memory').rglob('*.md'):
        rel = f.relative_to(root / 'memory').as_posix()
        if not any(x in rel for x in LAYER_SKIP):
            snap[rel] = count_lines(f)
    return snap


def layer(rel):
    if rel == 'LEDGER.md':
        return 'ledger'
    if rel.startswith('sessions/'):
        return 'L2'
    if rel.startswith('log/') or rel == 'CHANGELOG.md':
        return 'log'
    if rel == 'INDEX.md' or rel.startswith('team/'):
        return 'L0'
    return 'L1'


def short_name(rel):
    name = rel.rsplit('/', 1)[-1]
    if rel.startswith('sessions/') and len(name) > 34:
        name = name[:16] + '…' + name[-14:]
    return name if rel.startswith('sessions/') else rel


def pulse(old, new):
    """One-line summary of what changed in memory since the last snapshot, or ''."""
    parts = []
    for rel in sorted(set(old) | set(new)):
        o, n = old.get(rel), new.get(rel)
        if o == n or rel == 'LEDGER.md':
            continue
        if o is None:
            parts.append(f"{layer(rel)} {short_name(rel)} new ({n} lines)")
        elif n is None:
            parts.append(f"{layer(rel)} {short_name(rel)} removed")
        else:
            parts.append(f"{layer(rel)} {short_name(rel)} {n - o:+d}")
    if len(parts) > 4:
        parts = parts[:4] + [f"+{len(parts) - 4} more"]
    return ' · '.join(parts)


def age(seconds):
    for unit, size in (('d', 86400), ('h', 3600), ('m', 60)):
        if seconds >= size:
            return f"{int(seconds // size)}{unit} ago"
    return 'just now'


def freshest(root):
    files = [f for f in (root / 'memory').rglob('*.md')
             if f.name != 'LEDGER.md' and not any(x in f.as_posix() for x in LAYER_SKIP)]
    if not files:
        return None
    f = max(files, key=lambda x: x.stat().st_mtime)
    return age(time.time() - f.stat().st_mtime), f.relative_to(root / 'memory').as_posix()


def activity(root, days=7):
    """(sparkline, writes) of memory files modified per day over the last `days` days, oldest first."""
    ticks = '▁▂▃▄▅▆▇█'
    counts = [0] * days
    today = time.mktime(time.strptime(time.strftime('%Y-%m-%d'), '%Y-%m-%d'))
    for f in (root / 'memory').rglob('*.md'):
        if f.name == 'LEDGER.md' or any(x in f.as_posix() for x in LAYER_SKIP):
            continue
        m = f.stat().st_mtime
        d = 0 if m >= today else int((today - m) // 86400) + 1
        if 0 <= d < days:
            counts[days - 1 - d] += 1
    top = max(counts) or 1
    spark = ''.join('·' if c == 0 else ticks[min(7, round(c / top * 7))] for c in counts)
    return spark, sum(counts)


def clean(text, n=56):
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)                 # [label](link) -> label
    text = re.sub(r'\s*\((?:[0-9a-f]{8} L[\d-]+|code: [^)]*)\)', '', text)  # source tags
    text = re.sub(r'[`*]', '', text).strip(' .')
    return text if len(text) <= n else text[:n - 1].rstrip() + '…'


def section(path, heading):
    """Bullet text under '## <heading>' in a markdown file; placeholders like <...> are ignored."""
    out, on = [], False
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith('## '):
            on = heading.lower() in line.lower()
        elif on and line.lstrip().startswith(('- ', '* ')):
            t = line.lstrip()[2:].strip()
            if t and not t.startswith('<'):
                out.append(t)
    return out


def where_we_are(root):
    idx = root / 'memory' / 'INDEX.md'
    return section(idx, 'where we are') if idx.is_file() else []


def next_steps(root, sid):
    logs = [f for f in (root / 'memory' / 'sessions').glob('*.md') if f.name != 'README.md']
    logs.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    others = [f for f in logs if sid[:8] not in f.name]
    for f in (others or logs):
        steps = section(f, 'open threads')
        if steps:
            return steps, f
    return [], None


def l1_health(root, days=30):
    """(stalest (name, age_days) or None, count of 'reported, not yet verified' bullets)."""
    stale, unverified, today = None, 0, time.time()
    skip = {'sessions', 'log', '_templates', 'team'}
    for d in (root / 'memory').iterdir():
        if not d.is_dir() or d.name in skip or d.name.startswith('.'):
            continue
        for f in d.glob('*.md'):
            text = f.read_text(encoding='utf-8', errors='replace')
            unverified += len(section(f, 'not yet verified'))
            m = re.search(r'Last updated:\s*(\d{4}-\d{2}-\d{2})', '\n'.join(text.splitlines()[:8]))
            if m:
                try:
                    age_d = int((today - time.mktime(time.strptime(m.group(1), '%Y-%m-%d'))) // 86400)
                except ValueError:
                    continue
                if age_d >= days and (stale is None or age_d > stale[1]):
                    stale = (f'{d.name}/{f.name}', age_d)
    return stale, unverified


def l0_tokens(root):
    """Tokens CORTEX always puts in context: index + preferences + the CLAUDE.md block (~4 bytes/token)."""
    mem, size = root / 'memory', 0
    for f in (mem / 'INDEX.md', mem / 'team' / 'user-preferences.md'):
        size += f.stat().st_size if f.is_file() else 0
    claude = root / 'CLAUDE.md'
    if claude.is_file():
        m = re.search(r'<!-- CORTEX:BEGIN.*?<!-- CORTEX:END -->', claude.read_text(encoding='utf-8', errors='replace'), re.S)
        size += len(m.group(0).encode()) if m else 0
    return size // 4


def context_usage(root, sid, tp):
    """(l0_tok, {rel: tok} for L1/L2 files Claude read this chat, current context tokens or None).

    Reads only what is new in the transcript since the last turn (byte offset cached per chat).
    Counts Read tool calls on memory files; reads via shell commands are not seen.
    """
    sf = STATE_DIR / f'{sid}.ctx.json'
    st = json.loads(sf.read_text()) if sf.exists() else {}
    offset, reads, total = st.get('offset', 0), st.get('reads', {}), st.get('total')
    mem = str(root / 'memory') + os.sep
    with open(tp, 'rb') as f:
        f.seek(offset)
        data = f.read()
    end = data.rfind(b'\n') + 1
    for raw in data[:end].splitlines():
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        msg = d.get('message') if isinstance(d, dict) else None
        if not isinstance(msg, dict) or d.get('type') != 'assistant':
            continue
        u = msg.get('usage') or {}
        t = sum(u.get(k, 0) or 0 for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
        if t:
            total = t
        for part in msg.get('content') or []:
            if not (isinstance(part, dict) and part.get('type') == 'tool_use' and part.get('name') == 'Read'):
                continue
            inp = part.get('input') or {}
            fp = str(inp.get('file_path', ''))
            if not fp.startswith(mem):
                continue
            rel = fp[len(mem):]
            if rel in ('INDEX.md', 'team/user-preferences.md', 'LEDGER.md') or any(x in rel for x in LAYER_SKIP):
                continue
            try:
                size, nlines = os.path.getsize(fp), max(1, count_lines(fp))
            except OSError:
                continue
            frac = min(1.0, inp['limit'] / nlines) if isinstance(inp.get('limit'), int) else 1.0
            reads[rel] = max(reads.get(rel, 0), int(size / 4 * frac))
    STATE_DIR.mkdir(exist_ok=True)
    sf.write_text(json.dumps({'offset': offset + end, 'reads': reads, 'total': total}))
    return l0_tokens(root), reads, total


def ktok(n):
    return f'{n / 1000:.1f}k' if n >= 1000 else str(n)


def context_line(root, sid, tp):
    l0, reads, total = context_usage(root, sid, tp)
    l1 = {r: t for r, t in reads.items() if not r.startswith('sessions/')}
    l2 = {r: t for r, t in reads.items() if r.startswith('sessions/')}
    mem_tok = l0 + sum(reads.values())
    detail = f"L0 {ktok(l0)}"
    if l1:
        detail += f" · L1 {len(l1)} file{'s' * (len(l1) != 1)} {ktok(sum(l1.values()))}"
    if l2:
        detail += f" · L2 {len(l2)} log{'s' * (len(l2) != 1)} {ktok(sum(l2.values()))}"
    if total and total >= mem_tok:
        pct = mem_tok / total * 100
        filled = max(1 if mem_tok else 0, round(10 * mem_tok / total))
        gauge = '█' * filled + '░' * (10 - filled)
        return f"◈ memory in context  ▕{gauge}▏ {pct:.0f}%  {ktok(mem_tok)} of {ktok(total)} tok  ·  {detail}"
    return f"◈ memory in context  {ktok(mem_tok)} tok  ·  {detail}"


def session_start(data, root):
    sid, tp = data.get('session_id', ''), data.get('transcript_path', '')
    mode = recording_mode(root)
    state, rtext = ledger_row(root, sid)
    scan, gaps = {}, []
    lines = [f"CORTEX: this chat is {sid[:8]} (session {sid}); transcript {tp}. Recording: {mode}."]
    lines.append(f"This chat's ledger row: {state} {rtext}." if state else "This chat has no ledger row yet.")
    try:
        out = subprocess.run([sys.executable, str(HERE / 'ledger_scan.py'), str(root), '--current', sid, '--json'],
                             capture_output=True, text=True, timeout=20)
        scan = json.loads(out.stdout)
        todo = [f"{c['short']} {', '.join(f'{a}-{b}' for a, b in c['backfill'])}" for c in scan.get('chats', [])
                if c.get('backfill') and 'live' in (c.get('ranges') or '')]
        untracked = [c['short'] for c in scan.get('chats', []) if c.get('state') == 'untracked' and c.get('backfill')]
        gaps = todo
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
    context = ' '.join(lines)
    try:  # seed the snapshot so the first Stop pulse reports only this chat's changes
        STATE_DIR.mkdir(exist_ok=True)
        if data.get('source') in ('compact', 'clear'):  # earlier reads left the context
            (STATE_DIR / f'{sid}.ctx.json').unlink(missing_ok=True)
        (STATE_DIR / f'{sid}.snap.json').write_text(json.dumps(snapshot(root)))
    except Exception:
        pass
    if not logs_enabled(root):
        print(context)
        return
    l0, l1, l2 = memory_stats(root)
    spark, _ = activity(root)
    fresh = freshest(root)
    parts = [f"◉ CORTEX {mode}", f"{l1} topic{'s' * (l1 != 1)}", f"{l2} chat{'s' * (l2 != 1)} remembered", f"{spark} 7d"]
    if fresh:
        parts.append(f"last write {fresh[0]}")
    if gaps:
        parts.append(f"⚠ {len(gaps)} unlogged tail{'s' * (len(gaps) != 1)}, recovering")
    if data.get('source') == 'compact':
        parts.append('resumed after compaction')
    msg = '  ·  '.join(parts) + '  ·  /cortex status'
    print(json.dumps({'systemMessage': msg,
                      'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': context}}))


def nudge(root, sid, tp):
    """Return the checkpoint nudge text and its short on-screen form, or (None, None)."""
    mode = recording_mode(root).lower()
    if mode.startswith('paused'):
        return None, None
    state, rtext = ledger_row(root, sid)
    rs = ranges(rtext)
    if state == 'excluded' or any(k == 'paused' and b is None for k, a, b in rs):
        return None, None
    live = [r for r in rs if r[0] in ('live', 'mined')]
    if mode.startswith('manual') and not any(k == 'live' for k, a, b in rs):
        return None, None
    n = count_lines(tp)
    covered_to = max([b or a for k, a, b in live], default=0)
    if not live and n < MIN_UNTRACKED:
        return None, None
    STATE_DIR.mkdir(exist_ok=True)
    marker = STATE_DIR / f'{sid}.json'
    last = json.loads(marker.read_text()).get('nudged_at', 0) if marker.exists() else 0
    if n - max(covered_to, last) < NUDGE_EVERY:
        return None, None
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
    short = (f"▸ CORTEX checkpoint due  ·  {n - covered_to} unlogged lines "
             f"(ledger {covered_to} → transcript {n})")
    return msg, short


def stop(data, root):
    if data.get('stop_hook_active'):
        return
    sid, tp = data.get('session_id', ''), data.get('transcript_path', '')
    if not sid:
        return
    show = logs_enabled(root)
    pulse_line = ''
    try:  # live pulse: what actually changed in memory since the last turn
        STATE_DIR.mkdir(exist_ok=True)
        snap_file = STATE_DIR / f'{sid}.snap.json'
        new = snapshot(root)
        if snap_file.exists():
            pulse_line = pulse(json.loads(snap_file.read_text()), new)
        snap_file.write_text(json.dumps(new))
    except Exception:
        pass
    msg, short = (None, None)
    if tp and os.path.isfile(tp):
        msg, short = nudge(root, sid, tp)
    out = {}
    if msg:
        out['hookSpecificOutput'] = {'hookEventName': 'Stop', 'additionalContext': msg}
    shown = []
    if pulse_line:
        _, rtext = ledger_row(root, sid)
        live = [b or a for k, a, b in ranges(rtext) if k in ('live', 'mined')]
        shown.append(f"⟲ CORTEX synced  ·  {pulse_line}" + (f"  ·  ledger → {max(live)}" if live else ''))
    if short:
        shown.append(short)
    if tp and os.path.isfile(tp) and show:
        try:
            shown.append(context_line(root, sid, tp))
        except Exception:
            pass
    if shown and show:
        out['systemMessage'] = '\n'.join(shown)
    if out:
        print(json.dumps(out))


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
