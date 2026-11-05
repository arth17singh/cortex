#!/usr/bin/env python3
"""CORTEX v8 everyday tools: catch-up briefs, live cross-chat updates, compaction re-anchoring, subject timelines,
open items, the decision log and stale-memory checks. Deterministic (no model calls), read-only except
`decisions --write`, which renders memory/DECISIONS.md.

usage: cortex_tools.py brief [--since YYYY-MM-DD] [--root DIR]      what changed lately, across every chat
       cortex_tools.py timeline "<subject>" [--root DIR]             one subject's history, old -> new, with sources
       cortex_tools.py open-items [--root DIR]                       unresolved questions and proposals, oldest first
       cortex_tools.py decisions [--write] [--root DIR]              the decision log (decisions and rejections, why)
       cortex_tools.py verify [--root DIR]                           records whose code files changed or vanished
The hooks also call: meanwhile(root, session) for live updates from other chats (UserPromptSubmit) and
reanchor(root, session) after a compaction (SessionStart, source "compact").
"""
import argparse, json, os, re, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cortex_lib as L  # noqa: E402

STATE = Path(tempfile.gettempdir()) / 'cortex-hook'
KEY_TYPES = ('decision', 'rejection', 'status', 'fact', 'open', 'lesson', 'preference')


def ptr(r):
    s = r.get('source') or {}
    return f' (chat {s["chat"]} L{s["line"]})' if s.get('chat') and s.get('line') else ''


def line(r, why=True):
    kind = 'open, unconfirmed' if r['type'] == 'open' else r['type']
    w = f' — why: {r["why"]}' if why and r.get('why') else ''
    return f'- {kind} {r.get("valid_from")}: {r["statement"]}{w}{ptr(r)}'


def current(records):
    sup = L.superseded_ids(records)
    return [r for r in records if r['id'] not in sup], sup


# ---------------------------------------------------------------- brief: what changed lately

def brief(root, since=None, exclude_chat=None, limit=12):
    """Records added since `since` (an ISO date or datetime), newest first, grouped by kind; '' when none."""
    records = L.load_records(root)
    cur, sup = current(records)
    since = since or time.strftime('%Y-%m-%d', time.localtime(time.time() - 3 * 86400))
    # when it became true (valid_from), not when a backfill wrote it down
    new = [r for r in records if (r.get('valid_from') or '') >= since[:10]
           and r['type'] != 'relation' and (not exclude_chat or (r.get('source') or {}).get('chat') != exclude_chat[:8])]
    if not new:
        return ''
    order = {'decision': 0, 'rejection': 1, 'status': 2, 'open': 3, 'fact': 4, 'lesson': 5, 'preference': 6}
    new.sort(key=lambda r: (order.get(r['type'], 9), -(int((r.get('valid_from') or '0000-00-00').replace('-', '')))))
    chats = sorted({(r.get('source') or {}).get('chat') for r in new if (r.get('source') or {}).get('chat')})
    counts = {}
    for r in new:
        counts[r['type']] = counts.get(r['type'], 0) + 1
    plural = {'status': 'status changes', 'open': 'open items', 'fact': 'facts', 'lesson': 'lessons',
              'preference': 'preferences', 'decision': 'decisions', 'rejection': 'rejections'}
    head = (f'Since {since[:16]}: ' + ', '.join(f'{n} {plural.get(t, t) if n > 1 else t}' for t, n in
                                               sorted(counts.items(), key=lambda x: order.get(x[0], 9)))
            + (f' across chat{"s" if len(chats) > 1 else ""} {", ".join(chats)}' if chats else ''))
    out = [head]
    for r in new[:limit]:
        out.append(line(r) + (' [since replaced]' if r['id'] in sup else ''))
    if len(new) > limit:
        out.append(f'… {len(new) - limit} more: cortex_tools.py brief --since {since[:10]}')
    return '\n'.join(out)


# ---------------------------------------------------------------- live updates from other chats

def meanwhile(root, session_id, limit=3):
    """Decisions, rejections and status changes other chats recorded since this chat last looked. Lines, or []."""
    sid = (session_id or '')[:8]
    if not sid:
        return []
    STATE.mkdir(exist_ok=True)
    mark = STATE / f'{sid}.seen'
    try:
        seen = mark.read_text().strip()
    except OSError:
        seen = ''
    records = L.load_records(root)
    latest = max((r.get('recorded_at') or '' for r in records), default='')
    mark.write_text(latest or L.now_iso())
    if not seen:                                   # first prompt of this chat: the SessionStart brief covered it
        return []
    fresh = [r for r in records if (r.get('recorded_at') or '') > seen and r['type'] in ('decision', 'rejection', 'status')
             and (r.get('source') or {}).get('chat') not in (sid, None)]
    return [f'- other chat {r["source"]["chat"]}, {r.get("recorded_at", "")[11:16]}: {r["type"]}: {r["statement"]}'
            + (f' (why: {r["why"]})' if r.get('why') else '') for r in fresh[-limit:]]


# ---------------------------------------------------------------- after a compaction

def reanchor(root, session_id, limit=10):
    """What this chat itself decided, rejected and left open, to put back after its context was compacted."""
    sid = (session_id or '')[:8]
    records = L.load_records(root)
    cur, sup = current(records)
    mine = [r for r in cur if (r.get('source') or {}).get('chat') == sid and r['type'] in
            ('decision', 'rejection', 'open', 'status', 'preference')]
    if not mine:
        return ''
    mine.sort(key=lambda r: r.get('recorded_at') or '')
    return ('This chat\'s memory before the compaction (records, newest last; open any pointer with memory_open):\n'
            + '\n'.join(line(r) for r in mine[-limit:]))


# ---------------------------------------------------------------- one subject's history

def timeline(root, subject):
    import cortex_search as S
    records = L.load_records(root)
    ents, aliases = L.entities(records), L.load_aliases(root)
    terms = L.tokens(subject)
    names = S.link(terms, subject, ents, aliases) or S.link_weak(terms, ents, {}, set())[:3]
    if not names:
        n = L.norm_subject(subject)
        names = [s for s in ents if n in s or s in n][:3]
    if not names:
        return f'No subject matching "{subject}" in the records. Try memory_search.'
    sup = L.superseded_ids(records)
    rows = sorted((r for r in records if set(r.get('subjects', [])) & set(names)),
                  key=lambda r: (r.get('valid_from') or '', r.get('recorded_at') or ''))
    out = [f'Timeline of {", ".join(names)} ({len(rows)} records, old → new; "replaced" = superseded later):']
    for r in rows:
        tag = ' [replaced]' if r['id'] in sup else ''
        rel = f' {r["subjects"][0]} {r.get("rel")} {r["subjects"][1]}:' if r['type'] == 'relation' else ''
        out.append(f'- {r.get("valid_from")} {r["type"]}{rel} {r["statement"]}'
                   + (f' — why: {r["why"]}' if r.get('why') else '') + tag + ptr(r))
    return '\n'.join(out)


# ---------------------------------------------------------------- open items

def open_items(root, limit=15):
    cur, _ = current(L.load_records(root))
    rows = sorted((r for r in cur if r['type'] == 'open'), key=lambda r: r.get('valid_from') or '')
    if not rows:
        return 'No open questions or pending proposals.'
    props = [r for r in rows if r['statement'].lower().startswith('proposed')]
    qs = [r for r in rows if r not in props]
    out = [f'{len(rows)} open items ({len(qs)} questions, {len(props)} proposals awaiting a decision), oldest first. '
           'Settle one by recording the decision with supersedes=<id>.']
    for title, group in (('Questions', qs), ('Proposals', props)):
        if group:
            out.append(f'{title}:')
            out += [f'- [{r["id"]}] {r.get("valid_from")}: {r["statement"]}{ptr(r)}' for r in group[:limit]]
            if len(group) > limit:
                out.append(f'  … {len(group) - limit} more (open-items --all)')
    return '\n'.join(out)


# ---------------------------------------------------------------- decision log

def decisions(root, write=False):
    records = L.load_records(root)
    sup = L.superseded_ids(records)
    rows = sorted((r for r in records if r['type'] in ('decision', 'rejection')),
                  key=lambda r: (r.get('valid_from') or '', r.get('recorded_at') or ''))
    out = ['# Decision log', '',
           f'Generated by CORTEX from memory/records.jsonl on {L.today()} ({len(rows)} entries). Do not edit: record '
           'changes with memory_record (or cortex_write.py), and this file is regenerated. Struck-through entries were '
           'replaced later.', '']
    month = None
    for r in rows:
        m = (r.get('valid_from') or '')[:7]
        if m != month:
            out += ['', f'## {m}', '']
            month = m
        text = f'**{"Decided" if r["type"] == "decision" else "Rejected"}** ({r.get("valid_from")}): {r["statement"]}'
        if r['id'] in sup:
            text = f'~~{text}~~ → replaced by {sup[r["id"]]}'
        why = f' *Why:* {r["why"]}' if r.get('why') else ''
        out.append(f'- {text}{why} `{r["id"]}`{ptr(r)}')
    doc = '\n'.join(out) + '\n'
    if write:
        p = Path(root) / 'memory' / 'DECISIONS.md'
        tmp = p.with_suffix('.tmp')
        tmp.write_text(doc, encoding='utf-8')
        os.replace(tmp, p)
        return f'Wrote {p} ({len(rows)} entries).'
    return doc


# ---------------------------------------------------------------- stale memory

def verify(root):
    import cortex_search as S
    cur, _ = current(L.load_records(root))
    rows = []
    for r in cur:
        flags = S.staleness(root, r['statement'] + ' ' + (r.get('why') or ''), r.get('recorded_at') or r.get('valid_from'))
        if flags:
            rows.append((r, flags))
    if not rows:
        return 'No current record names a code file that has since changed or disappeared.'
    out = [f'{len(rows)} records name code files that changed or vanished since they were recorded; re-check them '
           'against the code and record the correction (supersedes=<id>) where they are wrong:']
    for r, f in rows:
        out.append(f'- [{r["id"]}] {r["type"]}: {r["statement"]} — {"; ".join(f)}{ptr(r)}')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('brief', 'timeline', 'open-items', 'decisions', 'verify'))
    ap.add_argument('subject', nargs='?')
    ap.add_argument('--since')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--root')
    a = ap.parse_args()
    root = L.find_root(a.root, explicit=bool(a.root))
    if not root:
        sys.exit('no CORTEX memory here')
    if a.cmd == 'brief':
        print(brief(root, a.since) or f'Nothing recorded since {a.since or "the last 3 days"}.')
    elif a.cmd == 'timeline':
        if not a.subject:
            ap.error('timeline needs a subject')
        print(timeline(root, a.subject))
    elif a.cmd == 'open-items':
        print(open_items(root, 10 ** 6 if a.all else 15))
    elif a.cmd == 'decisions':
        print(decisions(root, a.write))
    else:
        print(verify(root))


if __name__ == '__main__':
    main()
