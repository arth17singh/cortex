#!/usr/bin/env python3
"""Judge-free retrieval check of the production search: does the answer pack contain the lines answers come from?

usage: eval_retrieval.py --root PROJECT --questions Q.json [Q2.json ...] [--window 3] [--env K=V ...] [--label NAME]

For each question, runs cortex_search.search() exactly as Claude would, then counts a gold reference
("<chat8>:L<n>" or {"chat", "lines": "a-b"}) as covered when the pack holds
  - a record (current, rejected, or in a history chain) whose source is that chat within --window lines, or
  - an evidence item from that chat's archive whose line range overlaps it (within --window), or
  - a session-log chunk whose "(La-b)" tag overlaps it.
Prints aggregates only (never question text, references or expected answers), so the builder stays blind.
"""
import argparse, json, os, re, sys, time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_alt = next((sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == '--scripts' and i + 1 < len(sys.argv)), None)
sys.path.insert(0, _alt or str(REPO / 'skills' / 'cortex' / 'scripts'))   # --scripts DIR: score another version


def parse_ref(ref):
    if isinstance(ref, dict):
        nums = [int(x) for x in re.findall(r'\d+', ref.get('lines', ''))]
        return (ref.get('chat', '')[:8], min(nums), max(nums)) if nums else None
    m = re.match(r'([0-9a-f]{8}):L?(\d+)(?:\s*-\s*L?(\d+))?', ref or '')
    return (m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))) if m else None


SRC = {}


def covered(ref, p, win):
    chat, lo, hi = ref
    recs = p['current'] + p['rejected'] + [dict(x, source=x.get('source') or SRC.get(x.get('id'), {}))
                                            for c in p['history_chains'] for x in c]
    for r in recs:
        s = r.get('source') or {}
        if s.get('chat') == chat and s.get('line') and lo - win <= int(s['line']) <= hi + win:
            return True
    for e in p['evidence']:
        if e.get('kind') == 'chat':
            if e.get('chat') == chat and e['line'] - win <= hi and lo <= (e.get('line_to') or e['line']) + win:
                return True
        elif chat in e.get('file', ''):
            for a, b in re.findall(r'\(L(\d+)-(\d+)\)', e.get('text', '')):
                if int(a) - win <= hi and lo <= int(b) + win:
                    return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--questions', nargs='+', required=True)
    ap.add_argument('--window', type=int, default=3)
    ap.add_argument('--env', action='append', default=[])
    ap.add_argument('--label', default='')
    ap.add_argument('--scripts', help='directory of another cortex scripts version to score (e.g. extracted from git)')
    a = ap.parse_args()
    for kv in a.env:
        k, v = kv.split('=', 1)
        os.environ[k] = v
    import cortex_search as S
    qs = []
    for f in a.questions:
        for q in json.load(open(f)):
            q['_set'] = Path(f).stem
            qs.append(q)
    S.search(a.root, 'warm up the index')
    for line in open(Path(a.root) / 'memory' / 'records.jsonl', encoding='utf-8'):
        try:
            r = json.loads(line)
            SRC[r['id']] = r.get('source') or {}
        except (ValueError, KeyError):
            pass
    agg = defaultdict(lambda: [0, 0, 0, 0])       # hit refs, refs, questions with any hit, questions
    shown = []
    t0 = time.perf_counter()
    lat = []
    for q in qs:
        t1 = time.perf_counter()
        p = S.search(a.root, q['question'])
        lat.append(time.perf_counter() - t1)
        shown.append(len(S.render(p)))
        refs = [r for r in (parse_ref(x) for x in q.get('refs', [])) if r]
        res = [covered(r, p, a.window) for r in refs]
        for key in ('ALL', q['_set'], 'group:' + (q.get('group') or '-')):
            g = agg[key]
            g[0] += sum(res); g[1] += len(res); g[2] += any(res); g[3] += 1
    lat.sort()
    out = {k: {'ref_recall': round(v[0] / v[1], 3) if v[1] else None, 'any_hit': round(v[2] / v[3], 3), 'n': v[3]}
           for k, v in sorted(agg.items())}
    print(json.dumps({'label': a.label, 'window': a.window, 'env': a.env, 'results': out,
                      'chars_shown_mean': int(sum(shown) / max(1, len(shown))),
                      'latency_ms': {'p50': round(lat[len(lat) // 2] * 1000), 'p95': round(lat[int(len(lat) * .95)] * 1000)}}))


if __name__ == '__main__':
    main()
