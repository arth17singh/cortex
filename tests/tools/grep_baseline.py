#!/usr/bin/env python3
"""Judge-free retrieval check for plain grep over the chat archive and notes, on the same questions and metric as
eval_retrieval.py, so CORTEX search and grep can be compared by recall AND by how much text each puts in context.

usage: grep_baseline.py --root PROJECT --questions Q.json [Q2.json ...] [--window 3] [--budget 6000]

Modes (grep -i semantics: a line matches when it contains the term):
  all-words   every line containing any content word of the question            (max recall, max context)
  rarest-3    every line containing one of the question's 3 rarest words         (what an agent typically greps)
  ranked      all-words hits ranked by distinct question words per line, then rarity, cut at --budget characters
A gold reference counts as covered when a returned archive line lies in a block whose transcript line is within
--window of it, or a returned note line carries a (La-b) tag overlapping it. Prints aggregates only.
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'skills' / 'cortex' / 'scripts'))
import cortex_lib as L, cortex_index as I, cortex_search as S  # noqa: E402
from eval_retrieval import parse_ref  # noqa: E402


def load_lines(root):
    """[(chat or None, block L or None, (La,Lb) tags, text)] for every line of the archive and the notes."""
    out = []
    mem = Path(root) / 'memory'
    for f in sorted((mem / 'chats').glob('*.txt')):
        chat, cur = f.stem, None
        for ln in f.read_text(encoding='utf-8', errors='replace').split('\n'):
            m = re.match(r'\[L(\d+) ', ln)
            if m:
                cur = int(m.group(1))
            if ln.strip():
                out.append((chat, cur, [], ln))
    for f in sorted(mem.rglob('*.md')):
        rel = f.relative_to(mem).parts
        if rel[0] in ('chats', '.cache', '_templates', '.backups') or f.name in ('RULES.md', 'PROTOCOL.md', 'LEDGER.md'):
            continue
        sess = re.search(r'_([0-9a-f]{8})-', f.name)
        for ln in f.read_text(encoding='utf-8', errors='replace').split('\n'):
            if ln.strip():
                tags = [(int(a), int(b)) for a, b in re.findall(r'\(L(\d+)-(\d+)\)', ln)]
                out.append((sess.group(1) if sess else None, None, tags, ln))
    return out


def covered(ref, hits, win):
    chat, lo, hi = ref
    for c, blk, tags, _ in hits:
        if c != chat:
            continue
        if blk is not None and lo - win <= blk <= hi + win:
            return True
        if any(a - win <= hi and lo <= b + win for a, b in tags):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--questions', nargs='+', required=True)
    ap.add_argument('--window', type=int, default=3)
    ap.add_argument('--budget', type=int, default=6000)
    a = ap.parse_args()
    R = I.Reader(a.root)
    lines = load_lines(a.root)
    low = [x[3].lower() for x in lines]
    qs = [q for f in a.questions for q in json.load(open(f))]
    agg = defaultdict(lambda: [0, 0, 0, 0, 0])            # hit refs, refs, any-hit questions, questions, chars
    for q in qs:
        terms = [t for t in dict.fromkeys(L.tokens(q['question'])) if t not in S.COMMON and len(t) > 2]
        idf = {t: R.idf(t) for t in terms}
        rare = sorted(terms, key=lambda t: -idf[t])[:3]
        match = defaultdict(set)
        for i, s in enumerate(low):
            for t in terms:
                if t in s:
                    match[i].add(t)
        modes = {
            'all-words': sorted(match),
            'rarest-3': sorted(i for i, ts in match.items() if ts & set(rare)),
        }
        ranked = sorted(match, key=lambda i: (-len(match[i]), -sum(idf[t] for t in match[i])))
        pick, used = [], 0
        for i in ranked:
            n = len(lines[i][3])
            if used + n > a.budget:
                continue
            pick.append(i)
            used += n
        modes[f'ranked@{a.budget}'] = pick
        refs = [r for r in (parse_ref(x) for x in q.get('refs', [])) if r]
        for mode, idx in modes.items():
            hits = [lines[i] for i in idx]
            res = [covered(r, hits, a.window) for r in refs]
            g = agg[mode]
            g[0] += sum(res); g[1] += len(res); g[2] += any(res); g[3] += 1
            g[4] += sum(len(lines[i][3]) for i in idx)
    out = {m: {'ref_recall': round(v[0] / v[1], 3) if v[1] else None, 'any_hit': round(v[2] / v[3], 3),
               'chars_per_question': int(v[4] / v[3])} for m, v in agg.items()}
    print(json.dumps({'window': a.window, 'results': out}))


if __name__ == '__main__':
    main()
