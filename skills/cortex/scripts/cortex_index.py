#!/usr/bin/env python3
"""CORTEX v8 index: one incremental SQLite FTS5 index over everything memory holds, plus a subject graph.

usage: cortex_index.py --root DIR [--rebuild] [--stats]

What is indexed (each a "doc" with an exact pointer):
  rec:<id>             a record from memory/records.jsonl (typed fact, decision, rejection, relation, ...)
  md:<file>:<line>     a bullet or section of a curated file (INDEX.md, topic files, session logs)
  chat:<id8>:<a>:<k>   a passage of the chat archive (memory/chats/<id8>.txt), lines L<a>-L<b> of the transcript
A passage is also indexed under the facts that were extracted from its lines ("facts as keys": the raw text stays
the value, the records only add index terms). Ranking is our BM25 (k1 1.4, b .5) computed from FTS5 statistics;
FTS5 only generates candidates, so nothing has to be loaded per query and the index grows without slowing down.

The graph links subjects to the docs about them: a record to its subjects, a passage or note to the subjects it
names, subject to subject for typed relations, record to record for supersession. Personalized PageRank by forward
push (local: it touches only the neighbourhood of the query's seeds) turns it into a ranking signal.

The index lives in memory/.cache/index.sqlite (rebuildable, never committed) and is refreshed from file signatures:
only sources whose size or mtime changed are re-read.
"""
import argparse, json, math, os, re, sqlite3, sys, time
from collections import defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cortex_lib as L  # noqa: E402

SKIP_DIRS = {'_templates', '.backups', '.migrated-automemory', '.cache', 'chats'}
SKIP_FILES = ('RULES.md', 'PROTOCOL.md', 'LEDGER.md', 'GRAPH.md', 'entities.md')
PASSAGE_CHARS = 1200
K1, B = 1.4, .5
COMMON = set('take takes took control controls mean means work works happen change changes need needs want make keep '
             'start stop run runs set get gets give show tell know think plan plans used doing going right wrong good '
             'best better still again ever now today later earlier first last next long time times expire expires '
             'remind decide decided choose chose pick picked happened current currently consider considered'.split())
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS sources(path TEXT PRIMARY KEY, sig TEXT);
CREATE TABLE IF NOT EXISTS docs(rowid INTEGER PRIMARY KEY, did TEXT UNIQUE, kind TEXT, src TEXT, chat TEXT,
                                la INTEGER, lb INTEGER, text TEXT, toks TEXT, ntok INTEGER, rec TEXT);
CREATE INDEX IF NOT EXISTS docs_src ON docs(src);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(toks, tokenize="unicode61 tokenchars '-._/'");
CREATE VIRTUAL TABLE IF NOT EXISTS vocab USING fts5vocab(fts, 'row');
CREATE TABLE IF NOT EXISTS edges(a TEXT, b TEXT, w REAL);
CREATE INDEX IF NOT EXISTS edges_a ON edges(a);
CREATE TABLE IF NOT EXISTS deg(n TEXT PRIMARY KEY, d REAL);
"""


# ---------------------------------------------------------------- sources -> docs

def md_chunks(rel, text):
    """A curated file as retrievable chunks: (line, text). Session logs by section (and decision bullets), others by
    bullet, table row or long line under its heading."""
    lines = text.split('\n')
    out = []
    if rel.startswith('memory/sessions/'):
        head, start, buf = '', 1, []
        for i, ln in enumerate(lines, 1):
            if re.match(r'^#{2,3} ', ln):
                if buf:
                    out.append((start, head + '\n' + '\n'.join(buf[:30])))
                head, start, buf = ln.strip('# ').strip(), i, []
            elif ln.strip():
                buf.append(ln.strip())
                if re.match(r'^-\s+', ln) and re.search(r'decision|rejected|alternatives', head, re.I):
                    out.append((i, f'{head}: {ln.strip()[2:]}'))
        if buf:
            out.append((start, head + '\n' + '\n'.join(buf[:30])))
    else:
        head = ''
        for i, ln in enumerate(lines, 1):
            if ln.startswith('#'):
                head = ln.strip('# ').strip()
            elif ln.strip().startswith(('- ', '* ', '|')) or (ln.strip() and len(ln) > 40):
                out.append((i, f'{head}: {ln.strip()}' if head else ln.strip()))
    return out


def chat_passages(text):
    """The chat archive as passages of whole blocks, at most PASSAGE_CHARS each; a long message is split into pieces
    that keep its line number. Compaction summaries inside a chat repeat earlier lines and are skipped.
    -> [(la, lb, text)]"""
    blocks = [b.strip() for b in re.split(r'\n(?=\[L\d+ )', text) if re.match(r'\[L\d+ ', b.strip())]
    blocks = [b for k, b in enumerate(blocks) if k == 0 or 'COMPACTION SUMMARY' not in b[:80]]
    out, cur, size = [], [], 0

    def ln(b):
        return int(re.match(r'\[L(\d+)', b).group(1))

    def flush():
        if cur:
            out.append((ln(cur[0]), ln(cur[-1]), '\n'.join(cur)))
    for b in blocks:
        if len(b) > PASSAGE_CHARS:
            flush()
            cur, size = [], 0
            tag = re.match(r'\[L\d+[^\]]*\]', b).group(0)
            for k in range(0, len(b), PASSAGE_CHARS):
                piece = b[k:k + PASSAGE_CHARS]
                out.append((ln(b), ln(b), piece if k == 0 else tag + ' …' + piece))
            continue
        if size + len(b) > PASSAGE_CHARS and cur:
            flush()
            cur, size = [], 0
        cur.append(b)
        size += len(b)
    flush()
    return out


def sources(root):
    """{relative path: signature} of everything the index is built from."""
    mem = Path(root) / 'memory'
    out = {}
    for f in sorted(mem.rglob('*.md')):
        parts = f.relative_to(mem).parts
        if any(p in SKIP_DIRS for p in parts) or f.name in SKIP_FILES:
            continue
        st = f.stat()
        out[f.relative_to(root).as_posix()] = f'{st.st_size}:{st.st_mtime_ns}'
    for f in sorted((mem / 'chats').glob('*.txt')):
        st = f.stat()
        out[f.relative_to(root).as_posix()] = f'{st.st_size}:{st.st_mtime_ns}'
    rp = L.records_path(root)
    if rp.exists():
        st = rp.stat()
        out['memory/records.jsonl'] = f'{st.st_size}:{st.st_mtime_ns}'
    return out


# ---------------------------------------------------------------- the index

def db_path(root):
    return Path(root) / 'memory' / '.cache' / 'index.sqlite'


def connect(root):
    p = db_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    gi = p.parent / '.gitignore'
    if not gi.exists():
        gi.write_text('*\n')
    conn = sqlite3.connect(str(p), timeout=10)
    conn.executescript(SCHEMA)
    return conn


def _add(conn, did, kind, src, text, toks, chat=None, la=None, lb=None, rec=None):
    cur = conn.execute('INSERT OR REPLACE INTO docs(did, kind, src, chat, la, lb, text, toks, ntok, rec) '
                       'VALUES (?,?,?,?,?,?,?,?,?,?)', (did, kind, src, chat, la, lb, text, ' '.join(toks), len(toks),
                                                        json.dumps(rec, ensure_ascii=False) if rec else None))
    conn.execute('INSERT INTO fts(rowid, toks) VALUES (?, ?)', (cur.lastrowid, ' '.join(toks)))


def _drop(conn, src):
    rows = [r[0] for r in conn.execute('SELECT rowid FROM docs WHERE src = ?', (src,))]
    for rid in rows:
        conn.execute('DELETE FROM fts WHERE rowid = ?', (rid,))
    conn.execute('DELETE FROM docs WHERE src = ?', (src,))


def rec_text(r):
    return ' '.join([r['statement'], r.get('why') or '', ' '.join(r.get('subjects', [])), r['type'], r.get('rel') or ''])


def update(root, force=False):
    """Bring the index in line with the files. Returns a dict of what changed (empty when nothing did)."""
    root = Path(root)
    conn = connect(root)
    now = sources(root)
    old = dict(conn.execute('SELECT path, sig FROM sources'))
    if force:
        old = {}
        conn.execute('DELETE FROM docs')
        conn.execute('DELETE FROM fts')
    changed = {p for p, s in now.items() if old.get(p) != s} | {p for p in old if p not in now}
    if not changed:
        conn.close()
        return {}
    records = L.load_records(root)
    recs_changed = 'memory/records.jsonl' in changed
    # facts as keys: each passage is also indexed under the records drawn from its lines
    by_chat = defaultdict(list)
    for r in records:
        s = r.get('source') or {}
        if s.get('chat') and s.get('line'):
            by_chat[s['chat']].append((int(s['line']), r))
    redo_chats = {p for p in now if p.startswith('memory/chats/')} if recs_changed else \
        {p for p in changed if p.startswith('memory/chats/')}
    with conn:
        for p in changed | redo_chats:
            _drop(conn, p)
        if recs_changed and 'memory/records.jsonl' in now:
            for r in records:
                _add(conn, 'rec:' + r['id'], 'record', 'memory/records.jsonl', r['statement'], L.tokens(rec_text(r)),
                     chat=(r.get('source') or {}).get('chat'), la=(r.get('source') or {}).get('line'),
                     lb=(r.get('source') or {}).get('line'), rec=r)
        for p in sorted(changed | redo_chats):
            if p not in now or p == 'memory/records.jsonl':
                continue
            text = (root / p).read_text(encoding='utf-8', errors='replace')
            if p.startswith('memory/chats/'):
                chat = Path(p).stem
                facts = sorted(by_chat.get(chat, []), key=lambda x: x[0])
                for k, (a, b, t) in enumerate(chat_passages(text)):
                    keys = ' '.join(r['statement'] + ' ' + ' '.join(r.get('subjects', [])) for line, r in facts
                                    if a <= line <= b)   # facts as keys: statement and subjects only (type words are noise)
                    _add(conn, f'chat:{chat}:{a}:{k}', 'chat', p, t, L.tokens(t + ' ' + keys), chat=chat, la=a, lb=b)
            else:
                for line, t in md_chunks(p, text):
                    kind = 'map' if p.endswith(('INDEX.md', '_index.md', 'README.md')) else \
                        'log' if p.startswith('memory/sessions/') else 'topic'
                    _add(conn, f'md:{p}:{line}', kind, p, t, L.tokens(p + ' ' + t), la=line, lb=line)
        conn.execute('DELETE FROM sources')
        conn.executemany('INSERT INTO sources(path, sig) VALUES (?, ?)', now.items())
        n, total = conn.execute('SELECT COUNT(*), COALESCE(SUM(ntok), 0) FROM docs').fetchone()
        conn.execute("INSERT OR REPLACE INTO meta(k, v) VALUES ('n', ?)", (str(n),))
        conn.execute("INSERT OR REPLACE INTO meta(k, v) VALUES ('avgdl', ?)", (str(total / n if n else 0),))
        conn.execute("INSERT OR REPLACE INTO meta(k, v) VALUES ('built', ?)", (L.now_iso(),))
        build_graph(conn, records)
    conn.close()
    return {'changed_sources': len(changed | redo_chats), 'docs': n}


def build_graph(conn, records):
    """Subjects <-> docs, typed relations, supersession. Rebuilt whole (cheap at project scale)."""
    conn.execute('DELETE FROM edges')
    conn.execute('DELETE FROM deg')
    w = defaultdict(float)

    def link(a, b, x):
        if a != b:
            w[(a, b)] += x
            w[(b, a)] += x
    sup = L.superseded_ids(records)
    ents = L.entities(records)
    for r in records:
        for s in r.get('subjects', []):
            link('rec:' + r['id'], 's:' + s, 1)
        if r['type'] == 'relation' and len(r.get('subjects', [])) == 2 and r['id'] not in sup:
            link('s:' + r['subjects'][0], 's:' + r['subjects'][1], 2)
        if r.get('supersedes'):
            link('rec:' + r['id'], 'rec:' + r['supersedes'], 1)
    # a note or passage is linked to the subjects it names (all of the subject's content words appear in it)
    idf = {t: d for t, d in conn.execute('SELECT term, doc FROM vocab')}
    n = max(1, int(dict(conn.execute('SELECT k, v FROM meta')).get('n', '1')))
    stoks = {}
    for s, e in ents.items():
        t = [x for x in dict.fromkeys(L.tokens(s)) if x not in COMMON]
        if t and (len(t) > 1 or (len(t[0]) >= 4 and len(e['records']) >= 2)):
            stoks[s] = set(t)
    inv = defaultdict(set)
    for s, t in stoks.items():
        for x in t:
            inv[x].add(s)
    weight = lambda s: sum(math.log(1 + n / (1 + idf.get(x, 0))) for x in stoks[s])
    for did, toks in conn.execute("SELECT did, toks FROM docs WHERE kind != 'record'"):
        ts = set(toks.split())
        cands = set()
        for x in ts:
            if x in inv:
                cands |= inv[x]
        hit = sorted((s for s in cands if stoks[s] <= ts), key=lambda s: -weight(s))[:12]
        for s in hit:
            link(did, 's:' + s, 1)
    conn.executemany('INSERT INTO edges(a, b, w) VALUES (?,?,?)', [(a, b, x) for (a, b), x in w.items()])
    d = defaultdict(float)
    for (a, b), x in w.items():
        d[a] += x
    conn.executemany('INSERT INTO deg(n, d) VALUES (?,?)', d.items())


# ---------------------------------------------------------------- queries

class Reader:
    """Read side of the index for one search: BM25 over FTS5 candidates, neighbours and degrees for PPR."""

    def __init__(self, root):
        self.conn = connect(root)
        meta = dict(self.conn.execute('SELECT k, v FROM meta'))
        self.n = int(meta.get('n', '0') or 0)
        self.avgdl = float(meta.get('avgdl', '0') or 0) or 1.0
        self._graph, self._deg, self._df = None, {}, {}

    def df(self, terms):
        need = [t for t in set(terms) if t not in self._df]
        for i in range(0, len(need), 400):
            part = need[i:i + 400]
            q = 'SELECT term, doc FROM vocab WHERE term IN (%s)' % ','.join('?' * len(part))
            got = dict(self.conn.execute(q, part))
            for t in part:
                self._df[t] = got.get(t, 0)
        return {t: self._df.get(t, 0) for t in terms}

    def idf(self, t):
        f = self.df([t])[t]
        return math.log(1 + (self.n - f + .5) / (f + .5)) if f else 0.0

    def bm25(self, terms, limit=None):
        """[(score, did)] for docs containing any term, best first; our BM25 on FTS5's candidates."""
        limit = limit or int(os.environ.get('CORTEX_BM25_LIMIT', '400'))
        terms = [t for t in dict.fromkeys(terms) if t]
        if not terms or not self.n:
            return []
        df = self.df(terms)
        live = [t for t in terms if df[t]]
        if not live:
            return []
        match = ' OR '.join('"%s"' % t.replace('"', '') for t in live)
        rows = self.conn.execute('SELECT d.did, d.toks, d.ntok FROM fts JOIN docs d ON d.rowid = fts.rowid '
                                 'WHERE fts MATCH ? ORDER BY bm25(fts) LIMIT ?', (match, limit)).fetchall()
        idf = {t: math.log(1 + (self.n - df[t] + .5) / (df[t] + .5)) for t in live}
        out = []
        for did, toks, ntok in rows:
            tf = defaultdict(int)
            for x in toks.split():
                if x in idf:
                    tf[x] += 1
            s = 0.0
            for t, f in tf.items():
                s += idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * (ntok or 1) / self.avgdl))
            if s > 0:
                out.append((s, did))
        out.sort(reverse=True)
        return out

    def _load_graph(self):
        """The whole graph in memory, once per search: one query is far cheaper than one per push."""
        if self._graph is None:
            g = defaultdict(list)
            for a, b, w in self.conn.execute('SELECT a, b, w FROM edges'):
                g[a].append((b, w))
            self._graph = g
            self._deg = dict(self.conn.execute('SELECT n, d FROM deg'))
        return self._graph

    def neighbours(self, node):
        return self._load_graph().get(node, ())

    def degree(self, node):
        self._load_graph()
        return self._deg.get(node, 0.0)

    def ppr(self, seeds, alpha=.5, eps=None, max_push=None):
        """Personalized PageRank by forward push (Andersen, Chung, Lang 2006): local and fast."""
        eps = eps if eps is not None else float(os.environ.get('CORTEX_PPR_EPS', '1e-6'))
        max_push = max_push if max_push is not None else int(os.environ.get('CORTEX_PPR_PUSH', '50000'))
        tot = sum(seeds.values()) or 1.0
        r = {k: v / tot for k, v in seeds.items()}
        p = defaultdict(float)
        q, inq, pushes = deque(r), set(r), 0
        while q and pushes < max_push:
            u = q.popleft()
            inq.discard(u)
            ru, du = r.get(u, 0.0), self.degree(u)
            if du == 0:
                p[u] += ru
                r[u] = 0.0
                continue
            if ru / du < eps:
                continue
            pushes += 1
            p[u] += alpha * ru
            r[u] = 0.0
            share = (1 - alpha) * ru / du
            for v, w in self.neighbours(u):
                r[v] = r.get(v, 0.0) + share * w
                dv = self.degree(v)
                if v not in inq and dv and r[v] / dv >= eps:
                    q.append(v)
                    inq.add(v)
        return p

    def docs(self, dids):
        if not dids:
            return {}
        out = {}
        for i in range(0, len(dids), 400):
            part = dids[i:i + 400]
            q = 'SELECT did, kind, src, chat, la, lb, text, rec FROM docs WHERE did IN (%s)' % ','.join('?' * len(part))
            for did, kind, src, chat, la, lb, text, rec in self.conn.execute(q, part):
                out[did] = {'did': did, 'kind': kind, 'src': src, 'chat': chat, 'la': la, 'lb': lb, 'text': text,
                            'rec': json.loads(rec) if rec else None}
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()
    root = L.find_root(a.root, explicit=True)
    if not root:
        sys.exit('no CORTEX memory here')
    t0 = time.perf_counter()
    res = update(root, force=a.rebuild)
    res['seconds'] = round(time.perf_counter() - t0, 2)
    if a.stats:
        conn = connect(root)
        res['by_kind'] = dict(conn.execute('SELECT kind, COUNT(*) FROM docs GROUP BY kind'))
        res['edges'] = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
        res['db_kb'] = db_path(root).stat().st_size // 1024
    print(json.dumps(res))


if __name__ == '__main__':
    main()
