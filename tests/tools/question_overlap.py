#!/usr/bin/env python3
"""Keep test questions semantic: measure how many rare words a question shares with the transcript lines its answer
comes from. A question that repeats the source's distinctive words can be answered by keyword matching alone.

usage: question_overlap.py --root PROJECT --file QUESTIONS.json           check every question in a file
       question_overlap.py --root PROJECT --question "..." --ref <chat8>:L<a>-<b> [--ref ...]

Rare word = a content token (cortex tokenizer) whose idf in this project's index is >= --min-idf (default 3.0,
i.e. found in fewer than about 1 in 20 passages). PASS when the question shares at most --max-shared (default 1)
rare words with the evidence blocks. Abstention questions (no refs) are checked against nothing and always pass.
"""
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'skills' / 'cortex' / 'scripts'))
import cortex_lib as L, cortex_index as I  # noqa: E402


def evidence_text(root, ref):
    m = re.match(r'([0-9a-f]{8}):L?(\d+)(?:-L?(\d+))?', ref.strip())
    if not m:
        return ''
    chat, a = m.group(1), int(m.group(2))
    b = int(m.group(3) or a)
    f = Path(root) / 'memory' / 'chats' / f'{chat}.txt'
    if not f.exists():
        return ''
    out = []
    for blk in re.split(r'\n(?=\[L\d+ )', f.read_text(encoding='utf-8', errors='replace')):
        n = re.match(r'\[L(\d+) ', blk)
        if n and a <= int(n.group(1)) <= b:
            out.append(blk)
    return '\n'.join(out)


def check(R, root, question, refs, min_idf, max_shared):
    ev = ' '.join(evidence_text(root, r) for r in refs)
    if not refs:
        return True, [], 0
    if not ev.strip():
        return False, ['<no evidence text found for refs>'], 0
    qt = {t for t in L.tokens(question) if len(t) > 2 and R.idf(t) >= min_idf}
    shared = sorted(t for t in qt & set(L.tokens(ev)))
    return len(shared) <= max_shared, shared, len(ev)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--file')
    ap.add_argument('--question')
    ap.add_argument('--ref', action='append', default=[])
    ap.add_argument('--min-idf', type=float, default=3.0)
    ap.add_argument('--max-shared', type=int, default=1)
    a = ap.parse_args()
    R = I.Reader(a.root)
    if a.question:
        ok, shared, n = check(R, a.root, a.question, a.ref, a.min_idf, a.max_shared)
        print(json.dumps({'pass': ok, 'shared_rare_words': shared, 'evidence_chars': n}))
        return
    qs = json.load(open(a.file))
    fails = 0
    for q in qs:
        refs = [r if isinstance(r, str) else f"{r.get('chat', '')[:8]}:L{r.get('lines', '')}" for r in q.get('refs', [])]
        ok, shared, n = check(R, a.root, q['question'], refs, a.min_idf, a.max_shared)
        fails += not ok
        print(f"{q.get('id')}: {'PASS' if ok else 'FAIL'} shared={shared} evidence_chars={n}")
    print(f'{len(qs) - fails}/{len(qs)} pass')


if __name__ == '__main__':
    main()
