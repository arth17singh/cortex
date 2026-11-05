"""Local micro-benchmark: pure-Python (stdlib) BM25 and Personalized PageRank.

Synthetic data only (Zipf vocabulary, random graph); measures order of magnitude,
not retrieval quality. Python 3.9 compatible.
"""
import array
import gc
import heapq
import itertools
import marshal
import math
import os
import random
import resource
import statistics
import sys
import time
from collections import deque
from operator import itemgetter

OUT = os.path.dirname(os.path.abspath(__file__))


def make_corpus(n_docs, avg_len=80, vocab_size=50000, seed=0):
    rnd = random.Random(seed)
    weights = [1.0 / (r ** 1.07) for r in range(1, vocab_size + 1)]
    cum = list(itertools.accumulate(weights))
    vocab = ["t%d" % i for i in range(vocab_size)]
    docs = []
    for _ in range(n_docs):
        length = max(10, int(rnd.gauss(avg_len, avg_len * 0.4)))
        docs.append(rnd.choices(vocab, cum_weights=cum, k=length))
    return docs, vocab


def build_eager_index(docs, k1=0.9, b=0.4):
    """Term -> (doc ids, precomputed BM25 weights); scores fixed at index time."""
    postings = {}
    dl = []
    for d, toks in enumerate(docs):
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        dl.append(len(toks))
        for t, c in tf.items():
            p = postings.get(t)
            if p is None:
                p = postings[t] = ([], [])
            p[0].append(d)
            p[1].append(c)
    n = len(docs)
    avgdl = sum(dl) / n
    eager = {}
    for t, (ids, tfs) in postings.items():
        df = len(ids)
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        ws = [idf * c * (k1 + 1) / (c + k1 * (1 - b + b * dl[d] / avgdl))
              for d, c in zip(ids, tfs)]
        eager[t] = (ids, ws)
    return eager


def pack(eager):
    """Flat arrays + term -> (offset, length): loads with one memcpy per array."""
    ids_all = array.array("i")
    ws_all = array.array("f")
    offs = {}
    for t, (ids, ws) in eager.items():
        offs[t] = (len(ids_all), len(ids))
        ids_all.extend(ids)
        ws_all.extend(ws)
    return offs, ids_all, ws_all


def search_dict(eager, q, k=20):
    acc = {}
    get = acc.get
    for t in q:
        p = eager.get(t)
        if not p:
            continue
        for d, w in zip(p[0], p[1]):
            acc[d] = get(d, 0.0) + w
    return heapq.nlargest(k, acc.items(), key=itemgetter(1))


def search_packed(offs, ids_all, ws_all, q, k=20):
    acc = {}
    get = acc.get
    for t in q:
        o = offs.get(t)
        if not o:
            continue
        a, n = o
        for d, w in zip(ids_all[a:a + n], ws_all[a:a + n]):
            acc[d] = get(d, 0.0) + w
    return heapq.nlargest(k, acc.items(), key=itemgetter(1))


def make_queries(vocab, n_q=200, seed=7):
    rnd = random.Random(seed)
    typical, heavy = [], []
    for _ in range(n_q):
        # typical: 6 content terms from Zipf ranks 50..20000 (stopwords removed)
        typical.append([vocab[rnd.randint(50, 20000)] for _ in range(6)])
        # heavy: same plus 2 stopword-like terms from the top 20 ranks
        heavy.append(typical[-1] + [vocab[rnd.randint(0, 19)] for _ in range(2)])
    return typical, heavy


def time_queries(fn, queries):
    ts = []
    for q in queries:
        t0 = time.perf_counter()
        fn(q)
        ts.append((time.perf_counter() - t0) * 1000)
    ts.sort()
    return statistics.mean(ts), ts[int(len(ts) * 0.95) - 1]


def bench_bm25(n_docs):
    t0 = time.perf_counter()
    docs, vocab = make_corpus(n_docs)
    t_gen = time.perf_counter() - t0
    t0 = time.perf_counter()
    eager = build_eager_index(docs)
    t_build = time.perf_counter() - t0
    n_post = sum(len(v[0]) for v in eager.values())
    del docs
    gc.collect()
    typical, heavy = make_queries(vocab)
    d_typ = time_queries(lambda q: search_dict(eager, q), typical)
    d_hvy = time_queries(lambda q: search_dict(eager, q), heavy)

    # cache format 1: marshal of the dict of lists
    f1 = os.path.join(OUT, "idx_dict_%d.marshal" % n_docs)
    with open(f1, "wb") as fh:
        marshal.dump(eager, fh)
    # cache format 2: packed arrays
    offs, ids_all, ws_all = pack(eager)
    f2 = os.path.join(OUT, "idx_packed_%d.bin" % n_docs)
    with open(f2, "wb") as fh:
        marshal.dump((offs, ids_all.tobytes(), ws_all.tobytes()), fh)
    del eager
    gc.collect()

    t0 = time.perf_counter()
    with open(f1, "rb") as fh:
        eager2 = marshal.load(fh)
    t_load1 = time.perf_counter() - t0
    del eager2
    gc.collect()

    t0 = time.perf_counter()
    with open(f2, "rb") as fh:
        offs2, ib, wb = marshal.load(fh)
    ids2 = array.array("i")
    ids2.frombytes(ib)
    ws2 = array.array("f")
    ws2.frombytes(wb)
    t_load2 = time.perf_counter() - t0
    p_typ = time_queries(lambda q: search_packed(offs2, ids2, ws2, q), typical)
    p_hvy = time_queries(lambda q: search_packed(offs2, ids2, ws2, q), heavy)
    size1 = os.path.getsize(f1) / 1e6
    size2 = os.path.getsize(f2) / 1e6
    os.remove(f1)
    os.remove(f2)
    print("BM25 n_docs=%d postings=%d vocab_used=%d gen=%.1fs build=%.1fs"
          % (n_docs, n_post, len(offs2), t_gen, t_build))
    print("  dict index   query ms mean/p95: typical %.1f/%.1f  heavy %.1f/%.1f"
          % (d_typ + d_hvy))
    print("  packed index query ms mean/p95: typical %.1f/%.1f  heavy %.1f/%.1f"
          % (p_typ + p_hvy))
    print("  cache load: marshal(dict) %.3fs (%.0f MB)   packed arrays %.3fs (%.0f MB)"
          % (t_load1, size1, t_load2, size2))
    sys.stdout.flush()


def make_graph(n=10000, m=100000, seed=1):
    rnd = random.Random(seed)
    nodes = list(range(n))
    cum = list(itertools.accumulate(1.0 / ((i + 1) ** 0.8) for i in range(n)))
    src = rnd.choices(nodes, cum_weights=cum, k=m)
    dst = rnd.choices(nodes, k=m)
    adj = [[] for _ in range(n)]
    wts = [[] for _ in range(n)]
    for a, b in zip(src, dst):
        if a == b:
            continue
        w = 3.0 if rnd.random() < 0.2 else 1.0  # typed relation vs co-occurrence
        adj[a].append(b)
        wts[a].append(w)
        adj[b].append(a)
        wts[b].append(w)
    return adj, wts


def ppr_power(adj, wts, outw, seeds, damping=0.5, tol=1e-6, max_iter=100):
    n = len(adj)
    z = sum(seeds.values())
    reset = {s: w / z for s, w in seeds.items()}
    p = [0.0] * n
    for s, w in reset.items():
        p[s] = w
    it = 0
    for it in range(1, max_iter + 1):
        new = [0.0] * n
        for s, w in reset.items():
            new[s] = (1 - damping) * w
        dangling = 0.0
        for u in range(n):
            pu = p[u]
            if pu == 0.0:
                continue
            ow = outw[u]
            if ow == 0.0:
                dangling += pu
                continue
            f = damping * pu / ow
            for v, w in zip(adj[u], wts[u]):
                new[v] += f * w
        if dangling:
            for s, w in reset.items():
                new[s] += damping * dangling * w
        diff = sum(abs(a - b) for a, b in zip(new, p))
        p = new
        if diff < tol:
            break
    return p, it


def ppr_push(adj, wts, outw, seeds, damping=0.5, eps=1e-6):
    """Forward push (Andersen-Chung-Lang): touches only nodes near the seeds."""
    alpha = 1 - damping
    z = sum(seeds.values())
    r = {s: w / z for s, w in seeds.items()}
    p = {}
    queue = deque(r)
    queued = set(r)
    pushes = 0
    while queue:
        u = queue.popleft()
        queued.discard(u)
        ru = r.get(u, 0.0)
        du = outw[u]
        if du == 0.0 or ru < eps * du:
            continue
        pushes += 1
        p[u] = p.get(u, 0.0) + alpha * ru
        r[u] = 0.0
        f = damping * ru / du
        for v, w in zip(adj[u], wts[u]):
            rv = r.get(v, 0.0) + f * w
            r[v] = rv
            if v not in queued and rv >= eps * outw[v]:
                queue.append(v)
                queued.add(v)
    return p, pushes


def bench_ppr(n, m):
    adj, wts = make_graph(n, m)
    outw = [sum(w) for w in wts]
    rnd = random.Random(3)
    seed_sets = [{rnd.randrange(n): 1.0 for _ in range(4)} for _ in range(20)]
    tp, iters = [], []
    for seeds in seed_sets:
        t0 = time.perf_counter()
        _, it = ppr_power(adj, wts, outw, seeds)
        tp.append((time.perf_counter() - t0) * 1000)
        iters.append(it)
    print("PPR n=%d undirected_edges~%d  power-iteration (damping .5, L1 tol 1e-6): "
          "mean %.0f ms, max %.0f ms, iters %d-%d"
          % (n, m, statistics.mean(tp), max(tp), min(iters), max(iters)))
    for eps in (1e-4, 1e-6):
        tq, touched = [], []
        for seeds in seed_sets:
            t0 = time.perf_counter()
            p, _ = ppr_push(adj, wts, outw, seeds, eps=eps)
            tq.append((time.perf_counter() - t0) * 1000)
            touched.append(len(p))
        print("  forward push eps=%g: mean %.1f ms, max %.1f ms, nodes with mass %d-%d"
              % (eps, statistics.mean(tq), max(tq), min(touched), max(touched)))
    sys.stdout.flush()


if __name__ == "__main__":
    print("python", sys.version.split()[0])
    for n_docs in (10000, 50000, 100000):
        bench_bm25(n_docs)
    bench_ppr(10000, 50000)
    bench_ppr(10000, 100000)
    bench_ppr(30000, 300000)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print("peak RSS %.0f MB" % (rss / 1e6 if sys.platform == "darwin" else rss / 1e3))
