#!/usr/bin/env python3
"""CORTEX optional semantic layer: free, local, open-source embeddings through Ollama, fused with keyword ranking.

usage: cortex_embed.py --root DIR [--model all-minilm:l6-v2] [--stats]     embed every doc not embedded yet

Nothing here is required: without Ollama (or with CORTEX_EMBED unset) search is keyword-only, as before.
- Models: any Ollama embedding model (all Apache-licensed, run locally, no API cost): all-minilm:l6-v2 (fast),
  nomic-embed-text (stronger), mxbai-embed-large (strongest, slow on CPU). Pick with CORTEX_EMBED=<model>.
- Vectors are stored, L2-normalised float32, in the same SQLite index (table `vec`), computed incrementally: only
  docs without a vector for the chosen model are embedded, so a new chat turn costs a few embeddings.
- Query time: one embedding call (~50–150 ms on a laptop CPU), then cosine similarity over all vectors (numpy when
  available, else pure Python over the keyword candidates), fused with the keyword ranking by reciprocal rank.
"""
import argparse, array, json, math, os, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cortex_lib as L  # noqa: E402
import cortex_index as I  # noqa: E402

URL = os.environ.get('CORTEX_EMBED_URL', 'http://localhost:11434')
DOC_PREFIX = {'nomic-embed-text': 'search_document: '}
QUERY_PREFIX = {'nomic-embed-text': 'search_query: ',
                'mxbai-embed-large': 'Represent this sentence for searching relevant passages: '}
_CACHE = {}


def _prefix(table, model):
    return next((v for k, v in table.items() if model.startswith(k)), '')


def embed(model, texts, timeout=300):
    req = urllib.request.Request(URL + '/api/embed', data=json.dumps({'model': model, 'input': texts}).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())['embeddings']


def available(model):
    try:
        embed(model, ['ping'], timeout=10)
        return True
    except Exception:
        return False


def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return array.array('f', (x / n for x in v))


def ensure_table(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS vec(did TEXT, model TEXT, v BLOB, PRIMARY KEY(did, model))')


def doc_text(kind, text, rec):
    if rec:
        return ' '.join([rec.get('statement') or '', rec.get('why') or '', ' '.join(rec.get('subjects', []))])
    return (text or '')[:2000]


def update(root, model, batch=32, limit=None, progress=False):
    """Embed every doc that has no vector for `model` yet. Returns the number embedded."""
    I.update(root)
    conn = I.connect(root)
    ensure_table(conn)
    have = {d for (d,) in conn.execute('SELECT did FROM vec WHERE model = ?', (model,))}
    todo = [(d, k, t, r) for d, k, t, r in conn.execute('SELECT did, kind, text, rec FROM docs') if d not in have]
    live = {d for (d,) in conn.execute('SELECT did FROM docs')}
    conn.execute('DELETE FROM vec WHERE model = ? AND did NOT IN (SELECT did FROM docs)', (model,))
    if limit:
        todo = todo[:limit]
    pre, done, t0 = _prefix(DOC_PREFIX, model), 0, time.time()
    for i in range(0, len(todo), batch):
        part = todo[i:i + batch]
        texts = [pre + doc_text(k, t, json.loads(r) if r else None) for d, k, t, r in part]
        vecs = embed(model, texts)
        with conn:
            conn.executemany('INSERT OR REPLACE INTO vec(did, model, v) VALUES (?,?,?)',
                             [(d, model, _norm(v).tobytes()) for (d, _, _, _), v in zip(part, vecs)])
        done += len(part)
        if progress and (i // batch) % 10 == 0:
            print(f'{done}/{len(todo)} embedded, {done / max(1e-9, time.time() - t0):.1f}/s', flush=True)
    conn.close()
    _CACHE.pop((str(root), model), None)
    return done


def _matrix(root, model):
    """(dids, vectors) for a model, cached per process and refreshed when the index file changes."""
    key = (str(root), model)
    mtime = I.db_path(root).stat().st_mtime
    hit = _CACHE.get(key)
    if hit and hit[0] == mtime:
        return hit[1], hit[2]
    conn = I.connect(root)
    ensure_table(conn)
    rows = conn.execute('SELECT did, v FROM vec WHERE model = ?', (model,)).fetchall()
    conn.close()
    dids = [d for d, _ in rows]
    try:
        import numpy as np
        mat = np.frombuffer(b''.join(v for _, v in rows), dtype=np.float32).reshape(len(rows), -1) if rows else None
    except ImportError:
        mat = [array.array('f', v) for _, v in rows]
    _CACHE[key] = (mtime, dids, mat)
    return dids, mat


def dense(root, query, model, k=400, candidates=None):
    """[(similarity, did)] best first, for docs embedded with `model` (optionally only `candidates`)."""
    dids, mat = _matrix(root, model)
    if not dids:
        return []
    q = _norm(embed(model, [_prefix(QUERY_PREFIX, model) + query], timeout=30)[0])
    try:
        import numpy as np
        if isinstance(mat, list):
            raise ImportError
        sims = mat @ np.frombuffer(q.tobytes(), dtype=np.float32)
        idx = np.argsort(-sims)[:k]
        out = [(float(sims[i]), dids[i]) for i in idx]
    except ImportError:
        want = set(candidates) if candidates else None
        out = []
        for d, v in zip(dids, mat if isinstance(mat, list) else []):
            if want is None or d in want:
                out.append((sum(a * b for a, b in zip(q, v)), d))
        out.sort(reverse=True)
        out = out[:k]
    if candidates is not None:
        want = set(candidates)
        out = [x for x in out if x[1] in want] or out
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--model', default=os.environ.get('CORTEX_EMBED') or 'all-minilm:l6-v2')
    ap.add_argument('--stats', action='store_true')
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    root = L.find_root(a.root, explicit=True)
    if not root:
        sys.exit('no CORTEX memory here')
    if not available(a.model):
        sys.exit(f'Ollama model {a.model} not reachable at {URL} (install Ollama and `ollama pull {a.model}`)')
    t0 = time.time()
    n = update(root, a.model, limit=a.limit, progress=True)
    out = {'model': a.model, 'embedded': n, 'seconds': round(time.time() - t0, 1)}
    if a.stats:
        conn = I.connect(root)
        out['vectors'] = conn.execute('SELECT COUNT(*) FROM vec WHERE model = ?', (a.model,)).fetchone()[0]
        out['docs'] = conn.execute('SELECT COUNT(*) FROM docs').fetchone()[0]
    print(json.dumps(out))


if __name__ == '__main__':
    main()
