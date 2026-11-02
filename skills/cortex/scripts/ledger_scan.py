#!/usr/bin/env python3
"""CORTEX ledger scanner: what is tracked, what is not.

usage: ledger_scan.py [project_dir] [--json] [--preview] [--include-skipped] [--current SESSION_ID]
                      [--tz IANA_TZ] [--transcripts DIR] [--grep REGEX]

Lists the project's top-level Claude Code transcripts (one per chat, UUID-named), reads
memory/LEDGER.md, and reports for each chat its state, covered line ranges and uncovered gaps
(1-based, like `wc -l`). --preview adds the first real user message (80 chars) for chats that are
NOT excluded. --include-skipped treats skipped/paused ranges as uncovered (for `include`).
--current marks this chat so it is never reported as a backfill gap. A chat whose transcript changed
in the last 15 minutes and has a live range is flagged `active` (another open chat): never mine its
tail. --grep searches only non-excluded chats, outside skipped/paused ranges (for `recall`).
Excluded chats are never read beyond their line count and timestamps.
"""
import json, os, re, sys, tempfile, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

argv = sys.argv[1:]
def opt(name):
    if name in argv:
        i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
current, tdir_opt, grep, tzname = opt('--current'), opt('--transcripts'), opt('--grep'), opt('--tz')
flags = {x for x in argv if x.startswith('--')}
args = [x for x in argv if not x.startswith('--')]
proj = Path(args[0] if args else os.getcwd()).absolute()
base = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude') / 'projects'
cands = [Path(tdir_opt)] if tdir_opt else (
    [base / os.environ['CLAUDE_CODE_PROJECT_DIR_NAME']] if os.environ.get('CLAUDE_CODE_PROJECT_DIR_NAME') else
    [base / re.sub(r'[^A-Za-z0-9]', '-', str(p)) for p in (proj, proj.resolve())])
tdir = next((c for c in cands if c.is_dir()), cands[0])
ledger_path = proj / 'memory' / 'LEDGER.md'
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
KINDS = {'mined', 'live', 'skipped', 'paused'}
warnings = []
SECRET = re.compile(r'AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_\w+'
                    r'|xox[abpr]-[\w-]+|AIza[0-9A-Za-z_-]{35}|eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]*'
                    r'|(?i:(?:secret|passw(?:or)?d|token|api[_-]?key|access[_-]?key)\w*\s*[=:]\s*)\S+'
                    r'|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')
red = lambda s: SECRET.sub('[redacted]', s)

def parse_ranges(text, cid):
    """'mined 1-1200; live 1201-2925, 2930-2940; paused 500-' -> [(kind, a, b_or_None)]"""
    out, kind = [], None
    t = re.sub(r'\([^)]*\)', ' ', text.replace('`', '').replace('*', '')).replace('–', '-').replace('—', '-').lower()
    if t.strip() in ('', 'none', '-'): return out
    for part in re.split(r'[;,]', t):
        part = part.strip()
        if not part: continue
        m = re.fullmatch(r'(?:([a-z]+)\s+)?(\d+)\s*-\s*(\d*)', part) or re.fullmatch(r'(?:([a-z]+)\s+)?(\d+)()', part)
        if not m or not (m.group(1) or kind):
            warnings.append(f'{cid}: cannot parse range "{part}" (counted as NOT covered)'); continue
        kind = m.group(1) or kind
        if kind not in KINDS:
            warnings.append(f'{cid}: unknown range kind "{kind}" (counted as NOT covered)'); continue
        a = int(m.group(2)); b = (int(m.group(3)) if m.group(3) else None) if '-' in part else a
        out.append((kind, a, b))
    return out

ledger = {}
if ledger_path.exists():
    for row in ledger_path.read_text(encoding='utf-8').splitlines():
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        m = re.match(r'`?\s*([0-9a-f]{8})', cells[0]) if len(cells) >= 4 else None
        if not m: continue
        cid, state = m.group(1), re.sub(r'[^a-z]', '', cells[2].lower())
        rng = parse_ranges(cells[3], cid)
        excluded = 'excluded' in state or cells[3].replace('`', '').strip().lower() in ('none', '-', '—')
        if cid in ledger:
            warnings.append(f'{cid}: duplicate ledger rows, ranges merged; keep one row per chat')
            e = ledger[cid]; e['ranges'] += rng; e['raw'] += '; ' + cells[3]; e['excluded'] |= excluded
            if excluded: e['state'] = 'excluded'
        else:
            ledger[cid] = {'state': 'excluded' if excluded else state, 'ranges': rng, 'raw': cells[3], 'excluded': excluded}
elif (proj / 'memory' / 'INDEX.md').exists():
    warnings.append('memory/INDEX.md exists but memory/LEDGER.md is missing: rebuild the ledger (build.md Step 0) before mining')

def local(ts):
    try: return datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(ZoneInfo(tzname) if tzname else None).strftime('%Y-%m-%d %H:%M')
    except (ValueError, AttributeError): return None

def user_text(d):
    if d.get('type') != 'user' or d.get('isMeta') or d.get('isCompactSummary'): return None
    c = (d.get('message') or {}).get('content') if isinstance(d.get('message'), dict) else None
    txt = c if isinstance(c, str) else ' '.join(b.get('text', '') for b in (c or []) if isinstance(b, dict) and b.get('type') == 'text')
    args_ = re.search(r'<command-args>(.*?)</command-args>', txt, re.S)
    if '<command-name>' in txt:   # slash command: keep only "/name args"
        name = re.search(r'<command-name>(.*?)</command-name>', txt, re.S)
        txt = f"{name.group(1) if name else ''} {args_.group(1) if args_ else ''}".strip()
        if txt in ('/clear', '/compact', '/resume', '/exit'): return None
    txt = ' '.join(re.sub(r'<[^>]+>', ' ', txt).split())
    if not txt or txt.startswith(('Caveat', 'This session is being continued', 'The command below was run')): return None
    return txt

def meta(p, want_preview):
    n, first, last, preview, partial = 0, None, None, None, False
    with open(p, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.endswith('\n'): partial = True; break   # being written; wc -l does not count it
            n += 1
            try: d = json.loads(line)
            except ValueError: continue
            if not isinstance(d, dict): continue
            ts = d.get('timestamp')
            if isinstance(ts, str): first = first or ts; last = ts
            if want_preview and preview is None:
                t = user_text(d)
                if t: preview = red(t)[:80]
    return n, first, last, preview

# Per-transcript meta() cache: an active project has hundreds of chats, and re-reading all of them at
# every SessionStart would outgrow the hook's timeout. Only transcripts whose size or mtime changed are re-read.
CACHE = Path(tempfile.gettempdir()) / 'cortex-scan' / (re.sub(r'[^A-Za-z0-9]', '-', str(tdir))[-120:] + '.json')
try: cache = json.loads(CACHE.read_text())
except (OSError, ValueError): cache = {}
def meta_cached(p, want_preview):
    st = p.stat(); key = [st.st_size, st.st_mtime]; c = cache.get(p.stem)
    if isinstance(c, list) and len(c) == 3 and c[0] == key and (c[2] or not want_preview): return tuple(c[1])
    m = meta(p, want_preview); cache[p.stem] = [key, list(m), want_preview]; return m
def save_cache():
    try:
        CACHE.parent.mkdir(exist_ok=True); tmp = CACHE.with_suffix(f'.{os.getpid()}.tmp')
        tmp.write_text(json.dumps(cache)); os.replace(tmp, CACHE)
    except OSError: pass

def covered_set(entry, n, include_skipped):
    if entry['excluded']: return set(range(1, n + 1))
    cov = set()
    for kind, a, b in entry['ranges']:
        if include_skipped and kind in ('skipped', 'paused'): continue
        cov |= set(range(a, (b if b is not None else n) + 1))
    return cov

def blocked(entry, n):   # lines that must never be read (for --grep)
    if entry['excluded']: return set(range(1, n + 1))
    s = set()
    for kind, a, b in entry['ranges']:
        if kind in ('skipped', 'paused'): s |= set(range(a, (b if b is not None else n) + 1))
    return s

chats, files = [], []
if tdir.is_dir():
    for p in sorted(tdir.glob('*.jsonl'), key=lambda x: x.stat().st_mtime):
        if not UUID.match(p.stem): continue
        files.append(p)
        cid = p.stem[:8]
        entry = ledger.get(cid, {'state': 'untracked', 'ranges': [], 'raw': '', 'excluded': False})
        n, first, last, preview = meta_cached(p, '--preview' in flags and not entry['excluded'])
        cov = covered_set(entry, n, '--include-skipped' in flags)
        gaps, start = [], None
        for i in range(1, n + 2):
            if i <= n and i not in cov: start = start or i
            elif start: gaps.append((start, i - 1)); start = None
        is_current = bool(current) and p.stem == current
        active = (not is_current and any(k == 'live' for k, _, _ in entry['ranges'])
                  and time.time() - p.stat().st_mtime < 900)
        chats.append({'id': p.stem, 'short': cid, 'lines': n, 'first': local(first) if first else None,
                      'last': local(last) if last else None, 'state': entry['state'], 'ranges': entry['raw'],
                      'gaps': gaps, 'gap_lines': sum(b - a + 1 for a, b in gaps), 'preview': preview,
                      'current': is_current, 'active': active,
                      'backfill': [] if (entry['excluded'] or is_current) else
                                  [g for g in gaps if not (active and g[1] == n)]})
    save_cache()
    seen = {p.stem[:8] for p in files}
    for cid in ledger:
        if cid not in seen: warnings.append(f'{cid}: ledger row but no transcript (deleted by cleanupPeriodDays?)')
else:
    warnings.append(f'no transcript folder at {tdir}: wrong project dir, or transcripts moved (CLAUDE_CONFIG_DIR)')

if grep:
    rx = re.compile(grep, re.I)
    for p in files:
        e = ledger.get(p.stem[:8], {'ranges': [], 'excluded': False})
        if e['excluded']: continue
        with open(p, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        bad = blocked(e, len(lines))
        for i, line in enumerate(lines, start=1):
            m = rx.search(line)
            if m and i not in bad:
                print(f'{p.stem[:8]}:L{i}: ...{red(line[max(0, m.start() - 100):m.end() + 100].strip())}...')
    sys.exit(0)

backfill = sum(len(range(a, b + 1)) for c in chats for a, b in c['backfill'])
if '--json' in flags:
    print(json.dumps({'project': str(proj), 'transcripts': str(tdir), 'ledger': ledger_path.exists(),
                      'warnings': warnings, 'backfill_lines': backfill, 'chats': chats}, indent=1))
else:
    print(f'project: {proj}\ntranscripts: {tdir} ({"found" if tdir.is_dir() else "NONE"})\n'
          f'ledger: {"memory/LEDGER.md" if ledger_path.exists() else "missing"}\n')
    for c in chats:
        gap = ', '.join(f'{a}-{b}' for a, b in c['gaps']) or 'none'
        tag = ' [THIS CHAT]' if c['current'] else ' [ACTIVE in another chat: do not mine tail]' if c['active'] else ''
        print(f"{c['short']}  {(c['first'] or '?')[:10]}..{(c['last'] or '?')[:10]}  {c['lines']:>6} lines  "
              f"{c['state']:<9}  covered: {c['ranges'] or '-'}  gaps: {gap}{tag}")
        if c['preview']: print(f"          first message: {c['preview']}")
    for w in warnings: print(f'WARNING: {w}')
    print(f'\nlines to backfill (excludes excluded, this chat, active chats): {backfill}')
