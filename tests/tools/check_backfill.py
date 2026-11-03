#!/usr/bin/env python3
"""Audit backfilled records against their source transcripts (Step 6 acceptance).

usage: check_backfill.py <project root> <transcripts dir> [--tz IANA] [--show N]

For every record with provenance `transcript`, takes the statement's content terms (cortex_lib.tokens, 4+ chars or
containing a digit) and measures how many appear
  - in the chat it is attributed to (attribution: < 50% = misattributed), and
  - in the cited line's block and the two blocks either side (line precision: < 50% = imprecise line).
Prints counts, type and subject stats, supersession chains, and the worst cases.
"""
import argparse, json, re, subprocess, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'skills' / 'cortex' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import cortex_lib as L  # noqa: E402


def terms(s):
    return {t for t in L.tokens(s) if len(t) >= 4 or any(c.isdigit() for c in t)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('transcripts')
    ap.add_argument('--tz', default='America/Los_Angeles')
    ap.add_argument('--show', type=int, default=8)
    a = ap.parse_args()

    chats = {}
    for f in sorted(Path(a.transcripts).glob('*.jsonl')):
        text = subprocess.run([sys.executable, str(SCRIPTS / 'extract_transcript.py'), str(f), a.tz],
                              capture_output=True, text=True).stdout
        blocks = re.split(r'\n(?=\[L\d+ )', text)
        nums = [int(m.group(1)) if (m := re.match(r'\[L(\d+) ', b)) else 0 for b in blocks]
        chats[f.stem[:8]] = (set(L.tokens(text)), blocks, nums)

    recs = [r for r in L.load_records(a.root) if r.get('provenance') == 'transcript']
    sup = L.superseded_ids(recs)
    mis, imprecise, ok = [], [], 0
    for r in recs:
        chat = (r.get('source') or {}).get('chat')
        line = (r.get('source') or {}).get('line') or 0
        t = terms(r['statement'])
        if not t or chat not in chats:
            continue
        vocab, blocks, nums = chats[chat]
        att = len(t & vocab) / len(t)
        idx = max((k for k, n in enumerate(nums) if n <= line), default=0)
        near = set(L.tokens(' '.join(blocks[max(0, idx - 2):idx + 3])))
        prec = len(t & near) / len(t)
        if att < .5:
            mis.append((att, r))
        elif prec < .5:
            imprecise.append((prec, r))
        else:
            ok += 1
    types = Counter(r['type'] for r in recs)
    subj = Counter(s for r in recs for s in r['subjects'])
    print(json.dumps({'records': len(recs), 'current': sum(1 for r in recs if r['id'] not in sup),
                      'superseded': len(sup), 'types': dict(types), 'subjects': len(subj),
                      'subjects_used_once': sum(1 for v in subj.values() if v == 1),
                      'attributed_ok_and_line_precise': ok, 'line_imprecise': len(imprecise),
                      'misattributed': len(mis)}, indent=1))
    print('\ntop subjects:', subj.most_common(25))
    print('\nsupersession chains:')
    byid = {r['id']: r for r in recs}
    for r in recs:
        if r.get('supersedes') in byid:
            o = byid[r['supersedes']]
            print(f"  {o.get('valid_from')} {o['statement'][:110]}\n   -> {r.get('valid_from')} {r['statement'][:110]}")
    for name, rows in (('MISATTRIBUTED', mis), ('LINE IMPRECISE', imprecise)):
        print(f'\n{name} (worst {a.show}):')
        for score, r in sorted(rows, key=lambda x: x[0])[:a.show]:
            print(f"  {score:.2f} {r['source']} {r['statement'][:140]}")


if __name__ == '__main__':
    main()
