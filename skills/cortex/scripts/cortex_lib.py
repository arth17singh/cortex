#!/usr/bin/env python3
"""CORTEX v7 shared library: the record store, subjects (entities), the graph and ranked search.

Records live in memory/records.jsonl, one JSON object per line, append-only. Nothing is ever rewritten:
a record is "superseded" when a later record names it in `supersedes`, so history is never lost.
Only scripts write the file (cortex_write.py); the PreToolUse hook denies direct edits.

Stdlib only; Python 3.9+.
"""
import fcntl, json, math, os, re, secrets, time
from datetime import date, datetime, timezone
from pathlib import Path

TYPES = ('decision', 'rejection', 'fact', 'preference', 'status', 'lesson', 'open', 'relation')
RELS = ('uses', 'depends-on', 'part-of', 'owned-by', 'rejected-for', 'decided-in')
NEEDS_WHY = ('decision', 'rejection')
# record types that can contradict each other on the same subject
CLAIMS = {'decision', 'fact', 'status', 'preference', 'rejection'}
STOP = set('a an and are as at be but by for from has have i if in into is it its of on or our so that the their '
           'then there these this to was we were what when which will with you your can should would could do does '
           'did not no yes use used using also just only than very more most about over under after before'.split())


# ------------------------------------------------------------------ paths

def find_root(start=None):
    """The project root holding CORTEX memory (CLAUDE_PROJECT_DIR wins, then `start`, then cwd)."""
    for s in (os.environ.get('CLAUDE_PROJECT_DIR'), start, os.getcwd()):
        if not s:
            continue
        p = Path(s).resolve()
        for d in [p, *p.parents]:
            if (d / 'memory' / 'INDEX.md').is_file():
                return d
    return None


def records_path(root):
    return Path(root) / 'memory' / 'records.jsonl'


# ------------------------------------------------------------------ text

def tokens(text):
    """Lowercased content tokens; keeps identifiers like `billing-gate`, `p99`, `16`, `postgres-16` intact."""
    text = (text or '').lower()
    out = []
    for t in re.findall(r'[a-z0-9][a-z0-9._/-]*[a-z0-9]|[a-z0-9]', text):
        t = t.strip('.-/')
        if t and t not in STOP:
            out.append(t)
            if '-' in t or '/' in t:  # also index the parts of compound identifiers
                out += [p for p in re.split(r'[-/]', t) if p and p not in STOP]
    return out


def norm_subject(s):
    return re.sub(r'\s+', ' ', (s or '').strip().lower().strip('`"\''))


def overlap(a, b):
    """Jaccard overlap of the content tokens of two texts."""
    x, y = set(tokens(a)), set(tokens(b))
    return len(x & y) / len(x | y) if x and y else 0.0


# ------------------------------------------------------------------ records

def load_records(root):
    p = records_path(root)
    out = []
    if not p.is_file():
        return out
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get('id') and r.get('type') in TYPES:
            out.append(r)
    return out


def superseded_ids(records):
    """{old id: id of the record that replaced it}."""
    return {r['supersedes']: r['id'] for r in records if r.get('supersedes')}


def is_current(r, sup):
    return r['id'] not in sup


def append_record(root, rec):
    """Append one record under an exclusive lock, so concurrent chats never interleave or clobber lines."""
    p = records_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'a', encoding='utf-8') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def new_id(records):
    taken = {r['id'] for r in records}
    while True:
        i = 'r-' + secrets.token_hex(3)
        if i not in taken:
            return i


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


# ------------------------------------------------------------------ subjects (entities) and the graph

def load_aliases(root):
    """{alias: canonical subject} from memory/aliases.json (script-owned)."""
    p = Path(root) / 'memory' / 'aliases.json'
    try:
        data = json.loads(p.read_text())
        return {norm_subject(k): norm_subject(v) for k, v in data.items()}
    except (OSError, ValueError, AttributeError):
        return {}


def entities(records):
    """{subject: {'records': [ids], 'types': {type: n}, 'last': date}} over all records."""
    ents = {}
    for r in records:
        for s in r.get('subjects', []):
            e = ents.setdefault(s, {'records': [], 'types': {}, 'last': ''})
            e['records'].append(r['id'])
            e['types'][r['type']] = e['types'].get(r['type'], 0) + 1
            e['last'] = max(e['last'], r.get('valid_from') or '')
    return ents


def graph(records):
    """Weighted subject graph: {subject: {neighbour: {'weight': n, 'rels': set()}}}.

    Edges come from typed relation records (weight 3 each, labelled) and from subjects that share a record
    (co-occurrence, weight 1 each). Nothing is declared by hand.
    """
    sup = superseded_ids(records)
    g = {}

    def add(a, b, w, rel=None):
        if a == b:
            return
        for x, y in ((a, b), (b, a)):
            e = g.setdefault(x, {}).setdefault(y, {'weight': 0, 'rels': set()})
            e['weight'] += w
            if rel:
                e['rels'].add(rel if x == a else f'{rel} (inverse)')

    for r in records:
        if not is_current(r, sup):
            continue
        subs = r.get('subjects', [])
        if r['type'] == 'relation' and len(subs) == 2:
            add(subs[0], subs[1], 3, r.get('rel'))
        else:
            for i, a in enumerate(subs):
                for b in subs[i + 1:]:
                    add(a, b, 1)
    return g


def link_subject(name, ents, aliases):
    """(canonical, exact?, suggestions) for a subject name against known subjects and aliases."""
    n = norm_subject(name)
    if n in ents:
        return n, True, []
    if n in aliases:
        return aliases[n], True, []
    scored = []
    for s in ents:
        score = max(overlap(n, s), 0.9 if (n in s or s in n) and min(len(n), len(s)) >= 4 else 0)
        if score >= 0.34:
            scored.append((round(score, 2), s))
    scored.sort(reverse=True)
    return n, False, [s for _, s in scored[:3]]


# ------------------------------------------------------------------ ranked search (BM25 with an mtime-keyed cache)

class BM25:
    def __init__(self, docs, k1=1.4, b=0.75):
        """docs: list of (doc_id, text)."""
        self.ids = [d for d, _ in docs]
        self.toks = [tokens(t) for _, t in docs]
        self.n = len(docs)
        self.avg = sum(len(t) for t in self.toks) / self.n if self.n else 0
        df = {}
        for t in self.toks:
            for w in set(t):
                df[w] = df.get(w, 0) + 1
        self.idf = {w: math.log(1 + (self.n - f + .5) / (f + .5)) for w, f in df.items()}
        self.k1, self.b = k1, b
        self.tf = [{} for _ in self.toks]
        for i, t in enumerate(self.toks):
            for w in t:
                self.tf[i][w] = self.tf[i].get(w, 0) + 1

    def scores(self, query_terms):
        q = set(query_terms)
        out = []
        for i, tf in enumerate(self.tf):
            s, ln = 0.0, len(self.toks[i]) or 1
            for w in q:
                f = tf.get(w)
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * ln / (self.avg or 1)))
            if s > 0:
                out.append((s, self.ids[i]))
        out.sort(reverse=True)
        return out


def today():
    return date.today().isoformat()
