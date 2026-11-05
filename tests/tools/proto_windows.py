#!/usr/bin/env python3
"""Experiment (scratch, dev set only): how much answer evidence does Claude SEE per character, for different ways of
presenting the same search results? Metric: share of each question's must_include tokens that appear in the text
the tool returns (case-insensitive), and the size of that text. Aggregates only; the builder never sees the tokens.

usage: windows.py <project root>
"""
import json, re, sys
from pathlib import Path

REPO = Path('/Users/arthsingh/Developer/cortex')
sys.path.insert(0, str(REPO / 'skills/cortex/scripts'))
import cortex_lib as L, cortex_search as S, cortex_index as I  # noqa: E402

ROOT = sys.argv[1]
QS = [q for f in ('questions.json', 'questions-graph.json') for q in json.load(open(REPO / 'tests/eval-data/real' / f))]


def sentences(text):
    return [s for s in re.split(r'(?<=[.!?:;])\s+|\n+', text) if s.strip()]


def window(text, terms, idf, budget):
    """The sentences where the question's rare words occur (several together scores higher), with one neighbour on
    each side, in reading order, up to `budget` characters."""
    sents = sentences(text)
    if not sents:
        return ''
    q = {t: idf(t) for t in set(terms) if t not in S.COMMON}
    scores = []
    for i, s in enumerate(sents):
        toks = set(L.tokens(s))
        hit = [t for t in q if t in toks]
        scores.append((sum(q[t] for t in hit) * (1 + .5 * max(0, len(hit) - 1)), i))
    chosen, used = set(), 0
    for sc, i in sorted(scores, reverse=True):
        if sc <= 0:
            break
        for j in (i, i - 1, i + 1):
            if 0 <= j < len(sents) and j not in chosen and used + len(sents[j]) <= budget:
                chosen.add(j)
                used += len(sents[j]) + 1
    if not chosen:
        return sents[0][:budget]
    out, prev = [], None
    for j in sorted(chosen):
        if prev is not None and j != prev + 1:
            out.append('…')
        out.append(sents[j])
        prev = j
    return ' '.join(out)


def render_windows(p, terms, idf, per_passage, n_passages, rec_n=6):
    out = []
    for r in p['current'][:rec_n] + p['rejected'][:3]:
        out.append(f'{r["type"]} {r.get("valid_from")}: {r["statement"]}' + (f' — why: {r["why"]}' if r.get('why') else ''))
    for c in p['history_chains'][:2]:
        out.append('changed: ' + ' → '.join(x['statement'] for x in c))
    for e in p['evidence'][:n_passages]:
        out.append(f'{e["pointer"]}: ' + window(e['text'], terms, idf, per_passage))
    return '\n'.join(out)


def score(render):
    hit = tot = chars = 0
    for q in QS:
        mi = [m.lower() for m in q.get('must_include', []) if m]
        if not mi:
            continue
        text = render(q).lower()
        chars += len(text)
        hit += sum(1 for m in mi if m in text)
        tot += len(mi)
    n = sum(1 for q in QS if q.get('must_include'))
    return round(hit / tot, 3), int(chars / n)


if __name__ == '__main__':
    cache = {}
    R = I.Reader(ROOT)

    def pack(q):
        if q['id'] not in cache:
            cache[q['id']] = S.search(ROOT, q['question'], max_evidence=12)
        return cache[q['id']]
    print('answer tokens visible · median-ish avg chars shown, per question (dev set, 64 q)')
    print('A  current pack (records + 8 snippets of 320 chars):', score(lambda q: S.render(dict(pack(q), evidence=pack(q)['evidence'][:8]))))
    print('A2 current pack, passages shown in full (8):        ', score(lambda q: S.render(pack(q)) + '\n' + '\n'.join(e['text'] for e in pack(q)['evidence'][:8])))
    for per, n in ((400, 6), (600, 6), (600, 8), (900, 8), (1200, 10)):
        print(f'B  records + evidence windows, {n} passages × ≤{per} chars:',
              score(lambda q: render_windows(pack(q), L.tokens(q['question']), R.idf, per, n)))
