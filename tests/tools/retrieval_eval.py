#!/usr/bin/env python3
"""Judge-free retrieval check: does memory search surface the transcript lines an answer comes from?

usage: retrieval_eval.py --questions Q.json --arm ARM_DIR [--arm ARM_DIR ...] [--window 12] [--out FILE]

For each question and arm (a v7-layout arm; an arm whose settings set CORTEX_NO_GRAPH runs with the graph off):
  - runs cortex_search exactly as Claude would call it, plus the injection pack the UserPromptSubmit hook would add;
  - a question ref "<chat8>:L<line>" counts as covered when a returned record has source.chat == chat and a
    source line within --window lines, or a returned session-log chunk for that chat has a "(La-b)" range
    containing the line;
  - reports ref recall and any-hit rate per category and group, how often search abstains on not-in-memory
    questions (wanted) and on answerable ones (unwanted), and how often impact/connection output appears.
Prints aggregates only (never question text, refs or expected answers), so the builder stays blind.
"""
import argparse, json, os, re, sys
from collections import defaultdict
from pathlib import Path


def arm_env(arm):
    try:
        return (json.loads((Path(arm) / '.claude' / 'settings.json').read_text()).get('env') or {})
    except (OSError, ValueError):
        return {}


def covered(ref, pack, window):
    m = re.match(r'([0-9a-f]{8}):L(\d+)', ref)
    if not m:
        return None
    chat, line = m.group(1), int(m.group(2))
    recs = pack['current'] + pack['rejected']
    for c in pack['history_chains']:
        recs += c
    for r in recs:
        src = r.get('source') or {}
        if src.get('chat') == chat and src.get('line') and abs(int(src['line']) - line) <= window:
            return True
    for e in pack['evidence']:
        if chat in e['file']:
            for a, b in re.findall(r'\(L(\d+)-(\d+)\)', e['text']):
                if int(a) - window <= line <= int(b) + window:
                    return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--questions', required=True)
    ap.add_argument('--arm', action='append', required=True)
    ap.add_argument('--window', type=int, default=12)
    ap.add_argument('--out')
    a = ap.parse_args()
    qs = json.loads(Path(a.questions).read_text())
    report = {}
    for arm in a.arm:
        arm = str(Path(arm).resolve())
        skill = Path(arm).parent / '_skill-v7' / 'scripts'
        sys.path.insert(0, str(skill))
        import cortex_search as S, cortex_inject as I  # noqa: E402
        env = arm_env(arm)
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            agg = defaultdict(lambda: {'n': 0, 'refs': 0, 'hit_refs': 0, 'any_hit': 0, 'abstain': 0,
                                       'graph_q': 0, 'inject_any': 0})
            src = {r['id']: r.get('source') or {} for r in S.L.load_records(arm)}
            for q in qs:
                p = S.search(arm, q['question'])
                full = {**p, 'history_chains': [[dict(x, source=src.get(x['id'], {})) for x in c]
                                                for c in p['history_chains']]}
                inj = I.pack_text(p) if not p['abstain'] else []
                res = [covered(r, full, a.window) for r in q.get('refs', [])]
                res = [x for x in res if x is not None]
                for key in (q['category'], 'group:' + q.get('group', '?'), 'ALL'):
                    g = agg[key]
                    g['n'] += 1
                    g['refs'] += len(res)
                    g['hit_refs'] += sum(res)
                    g['any_hit'] += any(res)
                    g['abstain'] += bool(p['abstain'])
                    g['graph_q'] += bool(p.get('impact') or p.get('connection'))
                    g['inject_any'] += bool(inj)
            report[Path(arm).name] = {k: {'n': v['n'], 'ref_recall': round(v['hit_refs'] / v['refs'], 3) if v['refs'] else None,
                                          'any_hit': round(v['any_hit'] / v['n'], 3), 'abstain': round(v['abstain'] / v['n'], 3),
                                          'graph_queries_fired': v['graph_q'], 'injected': round(v['inject_any'] / v['n'], 3)}
                                      for k, v in agg.items()}
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            for m in ('cortex_search', 'cortex_inject', 'cortex_lib', 'cortex_render', 'cortex_hook'):
                sys.modules.pop(m, None)
            sys.path.remove(str(skill))
    arms = list(report)
    keys = sorted({k for r in report.values() for k in r}, key=lambda k: (k == 'ALL', k.startswith('group:'), k))
    lines = ['| category | ' + ' | '.join(f'{x} recall · any-hit · abstain' for x in arms) + ' |',
             '|---|' + '---:|' * len(arms)]
    for k in keys:
        cells = []
        for x in arms:
            r = report[x].get(k)
            cells.append('-' if not r else f"{r['ref_recall'] if r['ref_recall'] is not None else '-'} · {r['any_hit']} · {r['abstain']}")
        lines.append(f'| {k} (n={report[arms[0]][k]["n"]}) | ' + ' | '.join(cells) + ' |')
    lines.append('| graph queries fired (ALL) | ' + ' | '.join(str(report[x]['ALL']['graph_queries_fired']) for x in arms) + ' |')
    text = '\n'.join(lines)
    print(text)
    if a.out:
        Path(a.out).write_text(text + '\n\n```json\n' + json.dumps(report, indent=1) + '\n```\n')


if __name__ == '__main__':
    main()
