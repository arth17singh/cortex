#!/usr/bin/env python3
"""Record a decision, rejection, fact, preference, status, lesson, open item or relation in CORTEX memory.

usage: cortex_write.py --type T --subject S [--subject S2 ...] --statement TEXT [--why TEXT]
                       [--rel R] [--valid-from YYYY-MM-DD] [--supersedes ID | --coexists]
                       [--new-subject] [--provenance transcript|log|claude-stated|extracted]
                       [--session ID] [--line N] [--log PATH#HEADING] [--root DIR]

This is the only way records get written (memory/records.jsonl is append-only and script-owned).
Prints JSON. Exit codes:
  0  written (or an exact duplicate already exists: {"duplicate_of": id})
  2  bad arguments
  3  conflicts with current records: re-run with --supersedes <id> or --coexists
  4  a subject is new but close to existing ones: re-run with the existing name, or --new-subject
The PreToolUse hook adds --session and --line from the chat, so provenance is never typed by hand.
"""
import argparse, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cortex_lib as L  # noqa: E402


def fail(code, **payload):
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    sys.exit(code)


def conflict_threshold(new, old):
    """How similar two claims on a shared subject must be before one may contradict the other.

    Two decisions on a subject usually compete; two facts or statuses only if they say nearly the same thing
    (an update); a rejection contradicts a decision only when it rejects that very option.
    """
    pair = {new, old}
    if pair == {'decision'}:
        return .25
    if pair <= {'fact', 'status'}:
        return .35
    if pair == {'decision', 'rejection'}:
        return .6
    if pair == {'rejection'}:
        return .5
    return .5


def prune_pending(root, statement):
    """Drop queued (extracted, conflicting) items that this write resolves."""
    pend = Path(root) / 'memory' / '.pending.json'
    try:
        items = json.loads(pend.read_text())
    except (OSError, ValueError):
        return
    keep = [p for p in items if L.overlap((p.get('item') or {}).get('statement', ''), statement) < .6]
    if len(keep) != len(items):
        tmp = pend.with_suffix('.tmp')
        tmp.write_text(json.dumps(keep, ensure_ascii=False, indent=1))
        os.replace(tmp, pend)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--type', required=True, choices=L.TYPES)
    ap.add_argument('--subject', action='append', required=True)
    ap.add_argument('--statement', required=True)
    ap.add_argument('--why')
    ap.add_argument('--rel', choices=L.RELS)
    ap.add_argument('--valid-from')
    ap.add_argument('--supersedes')
    ap.add_argument('--coexists', action='store_true')
    ap.add_argument('--new-subject', action='store_true')
    ap.add_argument('--provenance', default='claude-stated', choices=('transcript', 'log', 'claude-stated', 'extracted'))
    ap.add_argument('--session')
    ap.add_argument('--line', type=int)
    ap.add_argument('--log')
    ap.add_argument('--root')
    a = ap.parse_args()

    root = L.find_root(a.root)
    if not root:
        fail(2, error='no CORTEX memory here (memory/INDEX.md not found)')
    if a.type in L.NEEDS_WHY and not (a.why or '').strip():
        fail(2, error=f'--why is required for a {a.type}: the reason is what makes it useful later')
    if a.type == 'relation' and (len(a.subject) != 2 or not a.rel):
        fail(2, error='a relation needs exactly two --subject values (from, to) and --rel')
    statement = ' '.join(a.statement.split())
    if len(statement) < 8:
        fail(2, error='--statement is too short to be useful')

    records = L.load_records(root)
    sup = L.superseded_ids(records)
    ents, aliases = L.entities(records), L.load_aliases(root)

    # 1. link subjects to existing ones; refuse silent near-duplicates of a subject name
    subjects, near = [], {}
    for s in a.subject:
        canon, exact, sugg = L.link_subject(s, ents, aliases)
        subjects.append(canon)
        if not exact and sugg and not a.new_subject:
            near[canon] = sugg
    if near:
        fail(4, error='new subject name close to existing ones', suggestions=near,
             fix='re-run with the existing subject name, or add --new-subject if it really is different')

    current = [r for r in records if L.is_current(r, sup)]

    # 2. exact duplicates are not written twice
    for r in current:
        if r['type'] == a.type and set(r.get('subjects', [])) == set(subjects) and L.overlap(r['statement'], statement) >= .85:
            print(json.dumps({'duplicate_of': r['id'], 'statement': r['statement']}, ensure_ascii=False))
            return

    # 3. conflicts: current claims about the same subjects that this one may contradict or replace
    if a.supersedes:
        target = next((r for r in records if r['id'] == a.supersedes), None)
        if not target:
            fail(2, error=f'--supersedes {a.supersedes}: no such record')
        if a.supersedes in sup:
            fail(2, error=f'{a.supersedes} is already superseded by {sup[a.supersedes]}; supersede that one instead')
    elif not a.coexists:
        conflicts = []
        for r in current:
            shared = set(r.get('subjects', [])) & set(subjects)
            if not shared:
                continue
            if a.type == 'relation' and r['type'] == 'relation':
                if r.get('subjects', [None])[0] == subjects[0] and r.get('rel') == a.rel:
                    conflicts.append(r)
            elif a.type in L.CLAIMS and r['type'] in L.CLAIMS:
                if L.overlap(r['statement'], statement) >= conflict_threshold(a.type, r['type']):
                    conflicts.append(r)
        if conflicts:
            fail(3, error='may conflict with current records', conflicts=[
                {'id': r['id'], 'type': r['type'], 'subjects': r['subjects'], 'statement': r['statement'],
                 'valid_from': r.get('valid_from')} for r in conflicts[:5]],
                 fix='re-run with --supersedes <id> if this replaces one of them, or --coexists if both stay true')

    rec = {
        'id': L.new_id(records), 'type': a.type, 'subjects': subjects, 'statement': statement,
        'why': ' '.join(a.why.split()) if a.why else None, 'rel': a.rel,
        'valid_from': a.valid_from or L.today(), 'supersedes': a.supersedes,
        'source': {'chat': (a.session or '')[:8] or None, 'line': a.line, 'log': a.log},
        'provenance': a.provenance, 'recorded_at': L.now_iso(),
    }
    L.append_record(root, rec)
    prune_pending(root, statement)
    try:                                   # keep the graph overlay (GRAPH.md, entities.md) in step with the records
        import cortex_render
        cortex_render.render(root)
    except Exception:
        pass
    neighbours = sorted({n for s in subjects for n in L.graph(records).get(s, {})})[:8]
    print(json.dumps({'id': rec['id'], 'subjects': subjects, 'supersedes': a.supersedes,
                      'new_subjects': [s for s in subjects if s not in ents], 'related': neighbours},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
