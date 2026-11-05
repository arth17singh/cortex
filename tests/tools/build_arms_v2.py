#!/usr/bin/env python3
"""Arms for the realistic eval round: one corpus, every memory method, everything else identical.

usage: build_arms_v2.py <arms dir> --corpus NAME --project DIR [--notes DIR] [--v5-project DIR]
                         [--embed-model all-minilm:l6-v2] [--only a,b]

<project> is a CORTEX test project (make_corpus.py, or a backfilled copy): memory/records.jsonl, memory/chats/, the
index with vectors in memory/.cache/, and the repository code next to memory/ when the corpus has code.
Arms (all outside the repo, same tool allowlist, same model and effort at run time):
  none          the code only (if any), no memory: what memory adds at all
  grep          the code + curated notes (if any) as notes/ + the chat archive as chats/, "grep them" in CLAUDE.md
  cortex-kw     v8.1: records + archive + index, native memory tools, inject + guard hooks, keyword search
  cortex-emb    same, embeddings only (CORTEX_EMBED_ONLY=1)
  cortex-hybrid same, keyword + embeddings fused (CORTEX_EMBED=<model>)
  v5            (with --v5-project) the curated v5 memory as it was, v5 session hook
The v8 skill is snapshotted into <arms dir>/_skill so later edits cannot change a running eval.
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL_SRC = REPO / 'skills' / 'cortex'
V5_SKILL = Path.home() / '.claude' / 'skills' / 'cortex.v5-backup-2026-11-04'
READ_ONLY = ['Bash(grep:*)', 'Bash(rg:*)', 'Bash(head:*)', 'Bash(tail:*)', 'Bash(sed -n:*)', 'Bash(cat:*)',
             'Bash(wc:*)', 'Bash(ls:*)', 'Bash(find:*)', 'Bash(cd:*)']
TOOLS = ['mcp__cortex__memory_search', 'mcp__cortex__memory_open', 'mcp__cortex__memory_timeline',
         'mcp__cortex__memory_brief']


def settings(path, hooks=None, allow=(), env=None):
    s = {'permissions': {'allow': READ_ONLY + list(allow)}}
    if hooks:
        s['hooks'] = hooks
    if env:
        s['env'] = env
    (path / '.claude').mkdir(parents=True, exist_ok=True)
    (path / '.claude' / 'settings.json').write_text(json.dumps(s, indent=1))


def code_only(src, dst):
    shutil.copytree(src, dst, symlinks=True, ignore=lambda d, names: ['memory', '.claude', '.mcp.json', 'CLAUDE.md']
                    if Path(d) == Path(src) else [])


def arm_none(dst, project, title):
    code_only(project, dst)
    (dst / 'CLAUDE.md').write_text(f'# {title}\n', encoding='utf-8')
    settings(dst)


def arm_grep(dst, project, notes, title):
    code_only(project, dst)
    if notes:
        shutil.copytree(notes, dst / 'notes', ignore=shutil.ignore_patterns(
            '_templates', '.backups', 'log', 'chats', '.cache', 'RULES.md', 'PROTOCOL.md', 'LEDGER.md', 'INDEX.md',
            'records.jsonl', 'aliases.json', 'GRAPH.md', 'entities.md', 'DECISIONS.md'))
    shutil.copytree(Path(project) / 'memory' / 'chats', dst / 'chats', ignore=shutil.ignore_patterns('.*'))
    where = '`notes/` (topic files and per-chat session logs) and ' if notes else ''
    (dst / 'CLAUDE.md').write_text(
        f'# {title}\n\n## Project memory\nThe project history is in {where}`chats/` (the full text of every past chat, one '
        'file per chat, each block tagged with its transcript line). Before answering a question about the project, '
        f'grep them (`grep -rn -i <term> {"notes/ " if notes else ""}chats/`) and read around the hits. If the answer '
        'is not there, say so instead of guessing.\n', encoding='utf-8')
    settings(dst)


def arm_cortex(dst, project, skill, title, env):
    shutil.copytree(project, dst, symlinks=True)
    mem = dst / 'memory'
    for p in mem.glob('log/backfill*'):
        p.unlink()
    shutil.copy(skill / 'reference' / 'rules.md', mem / 'RULES.md')
    stub = re.search(r'=====\n(<!-- CORTEX:BEGIN v8 -->.*?<!-- CORTEX:END -->)\n=====',
                     (skill / 'reference' / 'claude-block.md').read_text(), re.S).group(1).replace('{{SKILL_DIR}}', str(skill))
    md_path = dst / 'CLAUDE.md'
    md = md_path.read_text(encoding='utf-8') if md_path.exists() else f'# {title}\n'
    new = re.sub(r'<!-- CORTEX:BEGIN.*?<!-- CORTEX:END -->', lambda m: stub, md, flags=re.S)
    md_path.write_text(new if new != md else md.rstrip() + '\n\n' + stub + '\n', encoding='utf-8')
    pre = ''.join(f'{k}={v} ' for k, v in env.items())
    py = f'{pre}python3 {skill}/scripts/'
    hooks = {'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': py + 'cortex_inject.py', 'timeout': 15}]}],
             'PreToolUse': [{'matcher': 'Edit|Write|MultiEdit|Bash|Read|Grep|Glob|mcp__cortex__memory_record',
                             'hooks': [{'type': 'command', 'command': py + 'cortex_guard.py', 'timeout': 5}]}]}
    settings(dst, hooks, [f'Bash(python3 *{n}*)' for n in ('cortex_search.py', 'cortex_tools.py')] + TOOLS, env or None)
    (dst / '.mcp.json').write_text(json.dumps({'mcpServers': {'cortex': {
        'type': 'stdio', 'command': 'python3', 'args': [str(skill / 'scripts' / 'cortex_mcp.py')],
        'env': dict(env, CLAUDE_PROJECT_DIR=str(dst))}}}, indent=1))


def arm_v5(dst, v5_project):
    shutil.copytree(v5_project, dst, symlinks=True)
    settings(dst, {'SessionStart': [{'hooks': [{'type': 'command', 'timeout': 20,
                                                 'command': f'python3 {V5_SKILL}/scripts/cortex_hook.py'}]}]},
             [f'Bash(python3 *{n}*)' for n in ('ledger_scan.py', 'extract_transcript.py')])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arms')
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--project', required=True)
    ap.add_argument('--notes')
    ap.add_argument('--v5-project')
    ap.add_argument('--embed-model', default='all-minilm:l6-v2')
    ap.add_argument('--only')
    a = ap.parse_args()
    root = Path(a.arms).resolve()
    if REPO in [root, *root.parents]:
        sys.exit('arms must live outside the repo')
    root.mkdir(parents=True, exist_ok=True)
    skill = root / '_skill'
    if not skill.exists():
        shutil.copytree(SKILL_SRC, skill, ignore=shutil.ignore_patterns('__pycache__'))
    base = root / a.corpus
    base.mkdir(exist_ok=True)
    title = f'{a.corpus} (test project)'
    only = set((a.only or 'none,grep,cortex-kw,cortex-emb,cortex-hybrid,v5').split(','))
    plan = {
        'none': lambda d: arm_none(d, a.project, title),
        'grep': lambda d: arm_grep(d, a.project, a.notes, title),
        'cortex-kw': lambda d: arm_cortex(d, a.project, skill, title, {}),
        'cortex-emb': lambda d: arm_cortex(d, a.project, skill, title, {'CORTEX_EMBED': a.embed_model,
                                                                         'CORTEX_EMBED_ONLY': '1'}),
        'cortex-hybrid': lambda d: arm_cortex(d, a.project, skill, title, {'CORTEX_EMBED': a.embed_model}),
    }
    if a.v5_project:
        plan['v5'] = lambda d: arm_v5(d, a.v5_project)
    for name, build in plan.items():
        if name not in only:
            continue
        d = base / name
        if d.exists():
            shutil.rmtree(d)
        build(d)
        n = sum(1 for p in d.rglob('*') if p.is_file())
        print(f'{a.corpus}/{name}: {n} files')
    commit = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    (base / 'BUILD.json').write_text(json.dumps({'repo_commit': commit, 'project': a.project, 'embed_model': a.embed_model,
                                                 'arms': sorted(only & set(plan))}, indent=1))


if __name__ == '__main__':
    main()
