#!/usr/bin/env python3
"""Prototype (scratch only): does a transcript layer and/or a PPR graph re-rank surface more of the lines answers
come from? Judge-free ref recall on the DEV questions (questions.json + questions-graph.json). Aggregates only.

usage: proto.py <v7 project root>
"""
import json, os, re, subprocess, sys, time
from collections import defaultdict
from pathlib import Path

REPO = Path('/Users/arthsingh/Developer/cortex')
sys.path.insert(0, str(REPO / 'skills/cortex/scripts'))
import cortex_lib as L, cortex_search as S  # noqa: E402

ROOT = sys.argv[1]
TR = REPO / 'tests/eval-data/real/transcripts'
QS = [q for f in ('questions.json', 'questions-graph.json') for q in json.load(open(REPO / 'tests/eval-data/real' / f))]
WIN = int(os.environ.get('WIN', '12'))


# ---------------------------------------------------------------- transcript layer: line-addressed passages
def transcript_chunks(max_chars=1200):
    out = []
    for f in sorted(TR.glob('*.jsonl')):
        chat = f.stem[:8]
        text = subprocess.run([sys.executable, str(REPO / 'skills/cortex/scripts/extract_transcript.py'), str(f),
                               'America/Los_Angeles'], capture_output=True, text=True).stdout
        blocks = [b.strip() for b in re.split(r'\n(?=\[L\d+ )', text) if re.match(r'\[L\d+ ', b.strip())]
        blocks = [b for b in blocks if 'COMPACTION SUMMARY' not in b[:70]]
        cur, size = [], 0

        def flush():
            if cur:
                a = int(re.match(r'\[L(\d+)', cur[0]).group(1))
                b = int(re.match(r'\[L(\d+)', cur[-1]).group(1))
                out.append((f'transcripts/{chat}', 'chat', a, f'(L{a}-{b}) ' + '\n'.join(cur)))
        for bl in blocks:
            if len(bl) > max_chars:                      # a long message: pieces that keep its line number
                flush(); cur, size = [], 0
                n = re.match(r'\[L(\d+)[^\]]*\]', bl).group(0)
                for k in range(0, len(bl), max_chars):
                    piece = bl[k:k + max_chars]
                    out.append((f'transcripts/{chat}', 'chat', int(n[2:].split()[0]),
                                f'(L{n[2:].split()[0]}-{n[2:].split()[0]}) ' + (piece if k == 0 else n + ' ' + piece)))
                continue
            if size + len(bl) > max_chars and cur:
                flush(); cur, size = [], 0
            cur.append(bl); size += len(bl)
        flush()
    return out


# ---------------------------------------------------------------- index (built once per variant)
class Index:
    def __init__(self, root, with_transcripts):
        self.records = L.load_records(root)
        self.sup = L.superseded_ids(self.records)
        self.by_id = {r['id']: r for r in self.records}
        self.ents, self.aliases = L.entities(self.records), L.load_aliases(root)
        ch = [(rel, k, ln, t) for rel, k, ln, t in S.chunks(root)]
        if with_transcripts:
            ch += transcript_chunks()
        self.chunks = ch
        self.docs = [(f'rec:{r["id"]}', ' '.join([r['statement'], r.get('why') or '', ' '.join(r.get('subjects', [])),
                                                   r['type'], r.get('rel') or ''])) for r in self.records]
        exp = defaultdict(list)                    # key expansion: a passage is also indexed under the facts drawn from it
        if os.environ.get('KEYEXP') == '1':
            spans = defaultdict(list)
            for i, (rel, k, ln, t) in enumerate(ch):
                if rel.startswith('transcripts/'):
                    m = re.match(r'\(L(\d+)-(\d+)\)', t)
                    if m:
                        spans[rel[12:]].append((int(m.group(1)), int(m.group(2)), i))
            for r in self.records:
                src = r.get('source') or {}
                for a_, b_, i in spans.get(src.get('chat') or '', []):
                    if src.get('line') and a_ <= int(src['line']) <= b_:
                        exp[i].append(r['statement'] + ' ' + ' '.join(r.get('subjects', [])))
        self.docs += [(f'chk:{i}', f'{rel} {t} ' + ' '.join(exp.get(i, []))) for i, (rel, k, ln, t) in enumerate(ch)]
        self.bm = L.BM25(self.docs, b=.5)
        self.adj = self.build_graph()

    def build_graph(self):
        """Bipartite: subject nodes <-> doc nodes (records by their subjects; passages by subjects they mention),
        plus subject-subject edges for typed relations and record-record edges for supersession."""
        adj = defaultdict(lambda: defaultdict(float))

        def link(a, b, w):
            adj[a][b] += w
            adj[b][a] += w
        for r in self.records:
            if r['id'] in self.sup and r['type'] == 'open':
                pass
            for s in r.get('subjects', []):
                link(f'rec:{r["id"]}', 's:' + s, 1)
            if r['type'] == 'relation' and len(r.get('subjects', [])) == 2:
                link('s:' + r['subjects'][0], 's:' + r['subjects'][1], 2)
            if r.get('supersedes') in self.by_id:
                link(f'rec:{r["id"]}', f'rec:{r["supersedes"]}', 1)
        # passages mention subjects: all of a subject's content tokens appear in the passage
        stoks = {}
        for s in self.ents:
            t = [x for x in dict.fromkeys(L.tokens(s)) if x not in S.COMMON]
            if t and (len(t) > 1 or (len(t[0]) >= 4 and len(self.ents[s]['records']) >= 2)):
                stoks[s] = set(t)
        inv = defaultdict(set)
        for s, t in stoks.items():
            for x in t:
                inv[x].add(s)
        for i, (rel, k, ln, text) in enumerate(self.chunks):
            toks = set(L.tokens(text))
            cands = set().union(*(inv[x] for x in toks if x in inv)) if toks else set()
            hit = [s for s in cands if stoks[s] <= toks]
            hit.sort(key=lambda s: -sum(self.bm.idf.get(x, 0) for x in stoks[s]))
            for s in hit[:12]:
                link(f'chk:{i}', 's:' + s, 1)
        return adj

    def ppr(self, seeds, alpha=.5, iters=25):
        tot = sum(seeds.values()) or 1
        s = {k: v / tot for k, v in seeds.items()}
        x = dict(s)
        deg = {}
        for _ in range(iters):
            nxt = defaultdict(float)
            for n, v in x.items():
                nb = self.adj.get(n)
                if not nb:
                    continue
                d = deg.get(n)
                if d is None:
                    d = deg[n] = sum(nb.values())
                for m, w in nb.items():
                    nxt[m] += (1 - alpha) * v * w / d
            for k, v in s.items():
                nxt[k] += alpha * v
            x = nxt
        return x


def pack(ix, ranked):
    recs = [ix.by_id[d[4:]] for d in ranked if d.startswith('rec:')]
    cur = [r for r in recs if r['id'] not in ix.sup and r['type'] not in ('rejection', 'relation')][:6]
    rej = [r for r in recs if r['type'] == 'rejection' and r['id'] not in ix.sup][:5]
    chains, seen = [], set()
    for r in recs[:12]:
        c = S.chain(r['id'], ix.by_id, ix.sup)
        if len(c) > 1 and c[0]['id'] not in seen:
            seen.add(c[0]['id']); chains.append(c)
    ev = []
    taken = [((r.get('source') or {}).get('chat'), (r.get('source') or {}).get('line') or -999) for r in cur + rej]
    spans = []
    for d in ranked:
        if d.startswith('chk:') and len(ev) < 8:
            rel, k, ln, t = ix.chunks[int(d[4:])]
            if os.environ.get('DIVERSE') == '1' and rel.startswith('transcripts/'):
                m = re.match(r'\(L(\d+)-(\d+)\)', t)
                if m:
                    a_, b_, chat = int(m.group(1)), int(m.group(2)), rel[12:]
                    if any(c == chat and a_ - 3 <= l <= b_ + 3 for c, l in taken) or \
                            any(c == chat and not (b_ < x - 3 or a_ > y + 3) for c, x, y in spans):
                        continue                 # this passage's lines are already in the pack
                    spans.append((chat, a_, b_))
            ev.append({'file': rel, 'text': t})
    return {'current': cur, 'rejected': rej, 'history_chains': chains[:4], 'evidence': ev}


def rank(ix, q, ppr_w):
    terms = L.tokens(q)
    linked = S.link(terms, q, ix.ents, ix.aliases)
    linked += S.link_weak(terms, ix.ents, ix.bm.idf, set(linked))[:3]
    scored = ix.bm.scores(terms)

    def boost(sc, d):                        # the two main production boosts, so variants differ only in the graph
        if d.startswith('rec:'):
            sc *= 1.3
            if set(ix.by_id[d[4:]].get('subjects', [])) & set(linked):
                sc *= 1.6
        return sc
    base = sorted(((boost(sc, d), d) for sc, d in scored), reverse=True)
    if not ppr_w or not base:
        return [d for _, d in base]
    seeds = {('s:' + s): 1.0 for s in linked[:5]}
    top = base[0][0]
    for sc, d in base[:10]:
        seeds[d] = seeds.get(d, 0) + sc / top
    pr = ix.ppr(seeds)
    pr_rank = sorted(((v, d) for d, v in pr.items() if d.startswith(('rec:', 'chk:'))), reverse=True)
    rrf = defaultdict(float)
    for i, (_, d) in enumerate(base):
        rrf[d] += 1 / (60 + i)
    for i, (_, d) in enumerate(pr_rank):
        rrf[d] += ppr_w / (60 + i)
    return [d for d, _ in sorted(rrf.items(), key=lambda x: -x[1])]


def covered(ref, p):
    """ref: "<chat8>:L<line>" or {"chat": id8, "lines": "a-b"} (any line of the range counts)."""
    if isinstance(ref, dict):
        nums = [int(x) for x in re.findall(r'\d+', ref.get('lines', ''))]
        if not nums:
            return None
        chat, lo, hi = ref.get('chat', '')[:8], min(nums), max(nums)
    else:
        m = re.match(r'([0-9a-f]{8}):L(\d+)', ref)
        if not m:
            return None
        chat, lo, hi = m.group(1), int(m.group(2)), int(m.group(2))
    recs = p['current'] + p['rejected'] + [x for c in p['history_chains'] for x in c]
    for r in recs:
        src = r.get('source') or {}
        if src.get('chat') == chat and src.get('line') and lo - WIN <= int(src['line']) <= hi + WIN:
            return True
    for e in p['evidence']:
        if chat in e['file']:
            for a, b in re.findall(r'\(L(\d+)-(\d+)\)', e['text']):
                if int(a) - WIN <= hi and lo <= int(b) + WIN:
                    return True
    return False


def score(fn):
    hits = refs = anyhit = 0
    groups = defaultdict(lambda: [0, 0])
    t0 = time.perf_counter()
    for q in QS:
        p = fn(q['question'])
        res = [x for x in (covered(r, p) for r in q.get('refs', [])) if x is not None]
        hits += sum(res); refs += len(res); anyhit += any(res)
        g = groups['graph-set' if q['id'].startswith('G') else 'real-40']
        g[0] += sum(res); g[1] += len(res)
    dt = (time.perf_counter() - t0) / len(QS)
    return (round(hits / refs, 3), round(anyhit / len(QS), 3),
            {k: round(a / b, 3) for k, (a, b) in groups.items()}, round(dt * 1000))


def prod(graph_on):
    if graph_on:
        os.environ['CORTEX_GRAPH'] = '1'
    else:
        os.environ.pop('CORTEX_GRAPH', None)
    src = {r['id']: r.get('source') or {} for r in L.load_records(ROOT)}

    def fn(q):
        p = S.search(ROOT, q)
        p['history_chains'] = [[dict(x, source=src.get(x['id'], {})) for x in c] for c in p['history_chains']]
        return p
    return fn


if __name__ == '__main__':
    print(f'dev questions: {len(QS)}  window ±{WIN} lines   columns: ref recall · any-hit · per set · ms/query')
    print('production search, graph off :', score(prod(False)))
    print('production search, graph on  :', score(prod(True)))
    os.environ.pop('CORTEX_GRAPH', None)
    for tr in (False, True):
        t0 = time.perf_counter(); ix = Index(ROOT, tr); bt = time.perf_counter() - t0
        print(f'--- index {"WITH" if tr else "without"} transcript layer: {len(ix.docs)} docs, '
              f'{sum(len(v) for v in ix.adj.values()) // 2} graph edges, built in {bt:.2f}s')
        for w in (0, .5, 1, 2):
            print(f'  BM25{" + PPR w=" + str(w) if w else " only     "}:', score(lambda q: pack(ix, rank(ix, q, w))))
