#!/usr/bin/env python3
"""CORTEX status dashboard: a deterministic, read-only summary of a project's memory.

usage: cortex_status.py <project_dir> [--session <id>]

Prints activity, budget, what memory says is current, what's next, and anything needing attention.
Reuses the helpers in cortex_hook.py so the one-line startup status and this view never disagree.
"""
import glob, json, os, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cortex_hook as h  # noqa: E402

L0_BUDGET = 3000  # tokens


def l0_tokens(root):
    """Tokens CORTEX always loads: index + preferences + the CLAUDE.md block (~4 bytes per token)."""
    mem, size = root / 'memory', 0
    for f in (mem / 'INDEX.md', mem / 'team' / 'user-preferences.md'):
        size += f.stat().st_size if f.is_file() else 0
    claude = root / 'CLAUDE.md'
    if claude.is_file():
        m = re.search(r'<!-- CORTEX:BEGIN.*?<!-- CORTEX:END -->', claude.read_text(encoding='utf-8', errors='replace'), re.S)
        size += len(m.group(0).encode()) if m else 0
    return size // 4


def touches_memory(name, inp, mem):
    """Does this tool call read from the memory folder? (Read, Grep/Glob, or a shell command naming it.)"""
    if name == 'Bash':
        return mem in str(inp.get('command', '')) or 'memory/' in str(inp.get('command', ''))
    return any(str(inp.get(k, '')).startswith(mem) for k in ('file_path', 'path'))


def result_text(content):
    if isinstance(content, str):
        return content
    return ''.join(c.get('text', '') for c in content or [] if isinstance(c, dict))


def context_reads(root, sid):
    """(results, lines, tokens, context_total): memory text that came back into this chat's context.

    Measures the tool results themselves, so Read, cat, grep and sed all count. Resets at a compaction.
    """
    base = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude') / 'projects'
    found = glob.glob(str(base / '*' / f'{sid}.jsonl')) if sid else []
    if not found:
        return None
    mem = str(root / 'memory') + os.sep
    pending, results, lines, size, total = {}, 0, 0, 0, None
    with open(found[0], encoding='utf-8', errors='replace') as f:
        for raw in f:
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            if d.get('isCompactSummary') or d.get('subtype') == 'compact_boundary':
                pending, results, lines, size = {}, 0, 0, 0
                continue
            msg = d.get('message')
            if not isinstance(msg, dict) or not isinstance(msg.get('content'), list):
                continue
            u = msg.get('usage') or {}
            t = sum(u.get(k, 0) or 0 for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
            total = t or total
            for part in msg['content']:
                if not isinstance(part, dict):
                    continue
                if part.get('type') == 'tool_use' and touches_memory(part.get('name', ''), part.get('input') or {}, mem):
                    pending[part.get('id')] = True
                elif part.get('type') == 'tool_result' and pending.pop(part.get('tool_use_id'), None):
                    text = result_text(part.get('content'))
                    results += 1
                    lines += text.count('\n') + 1 if text else 0
                    size += len(text.encode())
    return results, lines, size // 4, total


def line_time(transcript, lineno):
    """Epoch seconds of the timestamp on a transcript line (1-based), or None."""
    try:
        with open(transcript, encoding='utf-8', errors='replace') as f:
            for i, raw in enumerate(f, 1):
                if i == lineno:
                    ts = json.loads(raw).get('timestamp', '')
                    return time.mktime(time.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S')) - time.timezone
    except (OSError, ValueError, AttributeError):
        pass
    return None


def settings(root):
    """(hooks installed, commit setting) read from the settings files and git."""
    hooks = False
    for f in (Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude') / 'settings.json',
              root / '.claude' / 'settings.json', root / '.claude' / 'settings.local.json'):
        try:
            hooks |= 'cortex_hook.py' in f.read_text()
        except OSError:
            pass
    git = subprocess.run(['git', '-C', str(root), 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True)
    if git.returncode != 0:
        commit = 'n/a (not a git repo)'
    else:
        ignored = subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', 'memory/INDEX.md']).returncode == 0
        commit = 'no (memory/ git-ignored)' if ignored else 'yes (memory/ tracked)'
    return hooks, commit


def bar(done, total, width=10):
    filled = min(width, round(width * done / total)) if total else 0
    return '█' * filled + '░' * (width - filled)


def main():
    args = sys.argv[1:]
    sid = args[args.index('--session') + 1] if '--session' in args else ''
    root = h.find_root(next((a for a in args if not a.startswith('--') and a != sid), '.'))
    if not root:
        print('CORTEX: no memory here (needs memory/INDEX.md and memory/LEDGER.md). Run /cortex start.')
        return
    mem = root / 'memory'
    mode = h.recording_mode(root)
    l0, l1, l2 = h.memory_stats(root)
    l0 = l0_tokens(root)
    spark, writes = h.activity(root)
    fresh = h.freshest(root)
    rule = '─' * 66

    print(f"◉ CORTEX status  ·  {mode}" + (f"  ·  chat {sid[:8]}" if sid else ''))
    print(rule)
    print(f"activity   {spark}  {writes} memory write{'s' * (writes != 1)} in 7 days"
          + (f"  ·  last {fresh[0]} ({fresh[1]})" if fresh else ''))
    print(f"budget     L0 {bar(l0, L0_BUDGET)} {l0 / 1000:.1f}k / {L0_BUDGET // 1000}k tok"
          f"  ·  {l1} L1 topic{'s' * (l1 != 1)}  ·  {l2} L2 chat log{'s' * (l2 != 1)}")

    reads = context_reads(root, sid)
    if reads:
        n, lines, tok, total = reads
        share = f"  ·  ~{(l0 + tok) / total * 100:.0f}% of this chat's {total / 1000:.1f}k context" if total else ''
        print(f"in context L0 {l0 / 1000:.1f}k tok always loaded  ·  pulled in this chat: {n} read{'s' * (n != 1)}, "
              f"{lines:,} lines, ~{tok / 1000:.1f}k tok{share}")

    now = h.where_we_are(root)
    for i, x in enumerate(now[:4]):
        print(('now        ▸ ' if i == 0 else '           ▸ ') + h.clean(x, 70))
    steps, src = h.next_steps(root, sid or 'none')
    for i, x in enumerate(steps[:4]):
        print(('next       ◦ ' if i == 0 else '           ◦ ') + h.clean(x, 70))

    pending = skipped = recorded = 0
    gaps, this = [], None
    try:
        out = subprocess.run([sys.executable, str(HERE / 'ledger_scan.py'), str(root), '--current', sid, '--json'],
                             capture_output=True, text=True, timeout=30)
        scan = json.loads(out.stdout)
        for c in scan.get('chats', []):
            if c.get('state') == 'excluded':
                continue
            for kind, a, b in h.ranges(c.get('ranges') or ''):
                span = max(0, (b if b is not None else c.get('lines', 0)) - a + 1)
                recorded += span if kind in ('live', 'mined') else 0
                skipped += span if kind == 'skipped' else 0
            pending += sum(y - x + 1 for x, y in c.get('backfill', []))
            if c.get('backfill') and 'live' in (c.get('ranges') or ''):
                gaps.append(c['short'])
            if c.get('current'):
                this = c
        print(f"ledger     {recorded:,} lines recorded  ·  {pending:,} pending  ·  {skipped:,} skipped on purpose")
        if this:
            live = [b or a for k, a, b in h.ranges(this.get('ranges') or '') if k in ('live', 'mined')]
            if live:
                end = min(max(live), this['lines'])
                saved = line_time(Path(scan.get('transcripts', '')) / f"{this['id']}.jsonl", end)
                behind = this['lines'] - end
                when = f"last saved to memory {h.age(time.time() - saved)}" if saved else f"saved through line {end}"
                print(f"this chat  {when}  \u00b7  " + (f"{behind} transcript lines since" if behind else 'fully saved'))
            else:
                print("this chat  not recording  \u00b7  /cortex start to record it")
        old_untracked = []
        for c in scan.get('chats', []):
            first = (c.get('first') or '')[:10]
            if c.get('state') == 'untracked' and c.get('backfill') and first:
                try:
                    if time.time() - time.mktime(time.strptime(first, '%Y-%m-%d')) > 25 * 86400:
                        old_untracked.append(c['short'])
                except ValueError:
                    pass
        warnings = scan.get('warnings', [])
    except Exception:
        warnings, old_untracked = ['ledger scan unavailable'], []

    watch = []
    if gaps:
        watch.append(f"{len(gaps)} chat{'s' * (len(gaps) != 1)} with unlogged tails ({', '.join(gaps[:3])})")
    stale, unverified = h.l1_health(root)
    if stale:
        watch.append(f"{stale[0]} not updated in {stale[1]} days")
    if unverified:
        watch.append(f"{unverified} fact{'s' * (unverified != 1)} still marked unverified")
    if l0 > L0_BUDGET:
        watch.append(f"L0 over budget ({l0:,} > {L0_BUDGET:,} tok)")
    elif l0 > 0.85 * L0_BUDGET:
        watch.append(f"L0 at {l0 / L0_BUDGET:.0%} of budget")
    if old_untracked:
        watch.append(f"{len(old_untracked)} untracked chat{'s' * (len(old_untracked) != 1)} near transcript expiry")
    watch += warnings[:2]
    hooks, commit = settings(root)
    if not hooks:
        watch.append('hooks not installed')
    logs = 'off' if not h.logs_enabled(root) else 'on'
    print(f"settings   recording {mode}  \u00b7  hooks {'\u2713' if hooks else '\u2717'}  \u00b7  logs {logs}  \u00b7  commit {commit}")
    print(rule)
    if watch:
        for i, w in enumerate(watch):
            print(('attention  \u26a0 ' if i == 0 else '           \u26a0 ') + w)
    else:
        print('attention  \u2713 nothing needs attention')

    if old_untracked or gaps:
        tip = '/cortex all  (recover unlogged and untracked chats)'
    elif l0 > 0.85 * L0_BUDGET:
        tip = '/cortex audit  (consolidate L0 back under budget)'
    elif not hooks:
        tip = '/cortex config hooks=install'
    elif stale or unverified:
        tip = '/cortex audit  (re-verify stale and unverified facts)'
    else:
        tip = None
    if tip:
        print(f"suggest    \u25b8 {tip}")


if __name__ == '__main__':
    main()
