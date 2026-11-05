"""Local check: stdlib sqlite3 FTS5 (C inverted index with bm25()) on synthetic chunks."""
import os
import random
import sqlite3
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_retrieval import make_corpus, make_queries  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
print("python", sys.version.split()[0], "sqlite", sqlite3.sqlite_version)
try:
    sqlite3.connect(":memory:").execute("create virtual table x using fts5(a)")
    print("FTS5 available")
except Exception as e:  # pragma: no cover
    print("FTS5 NOT available:", e)
    sys.exit(0)

for n_docs in (10000, 100000):
    db = os.path.join(OUT, "fts_%d.db" % n_docs)
    if os.path.exists(db):
        os.remove(db)
    docs, vocab = make_corpus(n_docs)
    t0 = time.perf_counter()
    con = sqlite3.connect(db)
    con.execute("create virtual table t using fts5(subject, body)")
    con.executemany("insert into t(subject, body) values (?, ?)",
                    ((" ".join(d[:3]), " ".join(d)) for d in docs))
    con.commit()
    t_build = time.perf_counter() - t0
    del docs
    typical, heavy = make_queries(vocab)
    sql = ("select rowid, bm25(t, 2.0, 1.0) from t where t match ? "
           "order by bm25(t, 2.0, 1.0) limit 20")
    res = {}
    for name, qs in (("typical", typical), ("heavy", heavy)):
        ts = []
        for q in qs:
            m = " OR ".join(q)
            s = time.perf_counter()
            con.execute(sql, (m,)).fetchall()
            ts.append((time.perf_counter() - s) * 1000)
        ts.sort()
        res[name] = (statistics.mean(ts), ts[int(len(ts) * 0.95) - 1])
    con.close()
    # cold process: new interpreter opens the db and runs one typical query
    q = " OR ".join(typical[0])
    code = ("import sqlite3;c=sqlite3.connect(%r);"
            "c.execute(%r,(%r,)).fetchall()" % (db, sql, q))
    cold = []
    for _ in range(10):
        s = time.perf_counter()
        subprocess.run([sys.executable, "-I", "-S", "-c", code], check=True)
        cold.append((time.perf_counter() - s) * 1000)
    print("FTS5 n_docs=%d build=%.1fs db=%.0f MB" % (n_docs, t_build, os.path.getsize(db) / 1e6))
    print("  in-process query ms mean/p95: typical %.1f/%.1f  heavy %.1f/%.1f"
          % (res["typical"] + res["heavy"]))
    print("  cold process (interpreter start + open + 1 query): median %.0f ms"
          % statistics.median(cold))
    os.remove(db)
    sys.stdout.flush()
