#!/usr/bin/env python3
"""Build the eval arms for the real corpus (Step 8), each a self-contained folder OUTSIDE the repo.

usage: build_arms.py <arms dir> [--v7-project tests/eval-data/real/project-v7]

Arms (same project text, same read-only tool allowlist, no Stop hooks: the eval measures answering):
  v5          the project copy as-is (v5 memory, curated map); hook: installed v5 cortex_hook.py SessionStart.
  grep        topic files + session logs copied to notes/, a short CLAUDE.md saying "grep notes/"; no hooks.
  v7          the backfilled copy (records + GRAPH.md + entities.md), v7 rules and stub; hooks: SessionStart,
              UserPromptSubmit (cortex_inject), PreToolUse (cortex_guard). Capture is off.
  v7-nograph  v7 minus the graph: no relation records, no GRAPH.md / entities.md, CORTEX_NO_GRAPH=1 (no expansion,
              impact or connection queries). Everything else identical to v7.
The v7 skill is snapshotted into <arms dir>/_skill-v7 so later code edits can't change a running eval.
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REAL = REPO / 'tests' / 'eval-data' / 'real'
V5_SKILL = Path.home() / '.claude' / 'skills' / 'cortex'
READ_ONLY = ['Bash(grep:*)', 'Bash(rg:*)', 'Bash(head:*)', 'Bash(tail:*)', 'Bash(sed -n:*)', 'Bash(cat:*)',
             'Bash(wc:*)', 'Bash(ls:*)', 'Bash(find:*)', 'Bash(cd:*)']


def settings(path, hooks=None, allow=(), env=None):
    s = {'permissions': {'allow': READ_ONLY + list(allow)}}
    if hooks:
        s['hooks'] = hooks
    if env:
        s['env'] = env
    (path / '.claude').mkdir(parents=True, exist_ok=True)
    (path / '.claude' / 'settings.json').write_text(json.dumps(s, indent=1))


def hook(cmd, timeout=10):
    return [{'hooks': [{'type': 'command', 'command': cmd, 'timeout': timeout}]}]


def script_allow(skill, names):
    # wildcard on both sides: Claude calls scripts by absolute or relative path, after `cd`, or piped into head
    return [f'Bash(python3 *{n}*)' for n in names]


def v7_arm(dst, src, skill, graph):
    shutil.copytree(src, dst)
    mem = dst / 'memory'
    for p in mem.glob('log/backfill*'):
        p.unlink()                                          # build logs are not memory
    shutil.copy(skill / 'reference' / 'rules.md', mem / 'RULES.md')
    stub = re.search(r'=====\n(<!-- CORTEX:BEGIN v7 -->.*?<!-- CORTEX:END -->)\n=====',
                     (skill / 'reference' / 'claude-block.md').read_text(), re.S).group(1)
    stub = stub.replace('{{SKILL_DIR}}', str(skill))
    env = {'CORTEX_GRAPH': '1'} if graph else None     # graph is opt-in since 2026-11-03
    if not graph:
        stub = stub.replace('@memory/GRAPH.md\n', '')
        for f in ('GRAPH.md', 'entities.md'):
            (mem / f).unlink(missing_ok=True)
        recs = [l for l in (mem / 'records.jsonl').read_text().splitlines()
                if l.strip() and json.loads(l).get('type') != 'relation']
        (mem / 'records.jsonl').write_text('\n'.join(recs) + '\n')
        rules = (mem / 'RULES.md').read_text()
        rules = rules.replace(', `GRAPH.md` (the subjects and how they connect, rendered from records)', '')
        rules = rules.replace(', impact ("what depends on X") and connection ("how is A linked to B") from the graph', '')
        (mem / 'RULES.md').write_text(rules)
        env = {'CORTEX_NO_GRAPH': '1'}
    md = (dst / 'CLAUDE.md').read_text()
    md = re.sub(r'<!-- CORTEX:BEGIN v5 -->.*?<!-- CORTEX:END -->', lambda m: stub, md, flags=re.S)
    (dst / 'CLAUDE.md').write_text(md)
    pre = 'CORTEX_NO_GRAPH=1 ' if not graph else 'CORTEX_GRAPH=1 '
    py = f'{pre}python3 {skill}/scripts/'
    hooks = {'SessionStart': hook(py + 'cortex_hook.py'),
             'UserPromptSubmit': hook(py + 'cortex_inject.py', 8),
             'PreToolUse': [{'matcher': 'Edit|Write|MultiEdit|Bash|Read|Grep|Glob',
                             'hooks': [{'type': 'command', 'command': py + 'cortex_guard.py', 'timeout': 5}]}]}
    settings(dst, hooks, script_allow(skill, ['cortex_search.py', 'ledger_scan.py', 'extract_transcript.py']), env)


def v8_arm(dst, src, skill, transcripts):
    """v8: records + chat archive + FTS5 index, v8 rules and block, native memory tools (MCP), inject + guard hooks."""
    shutil.copytree(src, dst)
    mem = dst / 'memory'
    for p in mem.glob('log/backfill*'):
        p.unlink()
    for d in ('chats', '.cache'):
        shutil.rmtree(mem / d, ignore_errors=True)
    subprocess.run([sys.executable, str(skill / 'scripts' / 'cortex_archive.py'), '--root', str(dst), '--all', '--index',
                    '--transcripts', str(transcripts), '--tz', 'America/Los_Angeles'], check=True, capture_output=True)
    shutil.copy(skill / 'reference' / 'rules.md', mem / 'RULES.md')
    stub = re.search(r'=====\n(<!-- CORTEX:BEGIN v8 -->.*?<!-- CORTEX:END -->)\n=====',
                     (skill / 'reference' / 'claude-block.md').read_text(), re.S).group(1).replace('{{SKILL_DIR}}', str(skill))
    md = (dst / 'CLAUDE.md').read_text()
    (dst / 'CLAUDE.md').write_text(re.sub(r'<!-- CORTEX:BEGIN.*?<!-- CORTEX:END -->', lambda m: stub, md, flags=re.S))
    py = f'python3 {skill}/scripts/'
    hooks = {'UserPromptSubmit': hook(py + 'cortex_inject.py', 10),
             'PreToolUse': [{'matcher': 'Edit|Write|MultiEdit|Bash|Read|Grep|Glob|mcp__cortex__memory_record',
                             'hooks': [{'type': 'command', 'command': py + 'cortex_guard.py', 'timeout': 5}]}]}
    tools = ['mcp__cortex__memory_search', 'mcp__cortex__memory_open', 'mcp__cortex__memory_timeline',
             'mcp__cortex__memory_brief']
    settings(dst, hooks, script_allow(skill, ['cortex_search.py', 'cortex_tools.py']) + tools)
    (dst / '.mcp.json').write_text(json.dumps({'mcpServers': {'cortex': {
        'type': 'stdio', 'command': 'python3', 'args': [str(skill / 'scripts' / 'cortex_mcp.py')],
        'env': {'CLAUDE_PROJECT_DIR': str(dst)}}}}, indent=1))


def grep_chats_arm(dst, v5_src, archive_dir):
    """Baseline: the same curated notes plus the same chat archive as plain text files, grep only."""
    (dst / 'notes').mkdir(parents=True)
    mem = v5_src / 'memory'
    for p in sorted(mem.rglob('*.md')):
        rel = p.relative_to(mem)
        if rel.parts[0] in ('_templates', '.backups', 'log') or rel.name in ('RULES.md', 'PROTOCOL.md', 'LEDGER.md', 'INDEX.md'):
            continue
        out = dst / 'notes' / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(p, out)
    shutil.copytree(archive_dir, dst / 'chats', ignore=shutil.ignore_patterns('.*'))
    head = re.sub(r'<!-- CORTEX:BEGIN v5 -->.*?<!-- CORTEX:END -->\n', '', (v5_src.parent / 'project' / 'CLAUDE.md').read_text(),
                  flags=re.S) if False else re.sub(r'<!-- CORTEX:BEGIN v5 -->.*?<!-- CORTEX:END -->\n', '',
                                                   (REAL / 'project' / 'CLAUDE.md').read_text(), flags=re.S)
    (dst / 'CLAUDE.md').write_text(head.replace('memory/', 'notes/') + '\n## Project notes\nProject notes are in `notes/` '
                                   '(topic files and per-chat session logs), and the full text of every past chat is in '
                                   '`chats/` (one file per chat, each block tagged with its transcript line). Before '
                                   'answering a question about the project, grep both (`grep -rn -i <term> notes/ chats/`) '
                                   'and read around the hits. If the answer is not there, say so instead of guessing.\n')
    settings(dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arms')
    ap.add_argument('--v7-project', default=str(REAL / 'project-v7'))
    ap.add_argument('--only', help='comma list of arms to build (default: all); v8 and grep-chats need --v7-project')
    a = ap.parse_args()
    arms = Path(a.arms).resolve()
    if REPO in [arms, *arms.parents]:
        sys.exit('arms must live outside the repo (its CLAUDE.local.md would load into every run)')
    if arms.exists():
        shutil.rmtree(arms)
    arms.mkdir(parents=True)
    skill = arms / '_skill-v7'
    shutil.copytree(REPO / 'skills' / 'cortex', skill, ignore=shutil.ignore_patterns('__pycache__'))

    # v5: as-is, installed v5 hook (read-only use of the installed skill)
    v5 = arms / 'v5'
    shutil.copytree(REAL / 'project', v5)
    settings(v5, {'SessionStart': hook(f'python3 {V5_SKILL}/scripts/cortex_hook.py')},
             script_allow(V5_SKILL, ['ledger_scan.py', 'extract_transcript.py']))

    # grep: same topic files and logs as plain notes
    g = arms / 'grep'
    (g / 'notes').mkdir(parents=True)
    mem = REAL / 'project' / 'memory'
    for p in sorted(mem.rglob('*.md')):
        rel = p.relative_to(mem)
        if rel.parts[0] in ('_templates', '.backups', 'log') or rel.name in ('RULES.md', 'PROTOCOL.md', 'LEDGER.md',
                                                                              'INDEX.md'):
            continue
        out = g / 'notes' / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(p, out)
    head = re.sub(r'<!-- CORTEX:BEGIN v5 -->.*?<!-- CORTEX:END -->\n', '', (REAL / 'project' / 'CLAUDE.md').read_text(),
                  flags=re.S)
    (g / 'CLAUDE.md').write_text(head.replace('memory/', 'notes/') + '\n## Project notes\nProject notes are in `notes/` '
                                 '(topic files and per-chat session logs). Before answering a question about the project, '
                                 'grep them (`grep -rn -i <term> notes/`) and read around the hits. If the answer is not in '
                                 'the notes, say so instead of guessing.\n')
    settings(g)

    only = set((a.only or 'v5,grep,v7,v7-nograph,v8,grep-chats').split(','))
    if 'v7' in only:
        v7_arm(arms / 'v7', Path(a.v7_project), skill, graph=True)
    if 'v7-nograph' in only:
        v7_arm(arms / 'v7-nograph', Path(a.v7_project), skill, graph=False)
    if 'v8' in only:
        v8_arm(arms / 'v8', Path(a.v7_project), skill, REAL / 'transcripts')
    if 'grep-chats' in only:
        grep_chats_arm(arms / 'grep-chats', REAL / 'project', arms / 'v8' / 'memory' / 'chats')
    commit = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--short', 'HEAD'], capture_output=True,
                            text=True).stdout.strip()
    (arms / 'BUILD.json').write_text(json.dumps({'repo_commit': commit, 'v7_project': a.v7_project,
                                                 'arms': ['v5', 'grep', 'v7', 'v7-nograph']}, indent=1))
    for arm in ('v5', 'grep', 'v7', 'v7-nograph', 'v8', 'grep-chats'):
        if not (arms / arm).exists():
            continue
        n = sum(1 for _ in (arms / arm).rglob('*') if _.is_file())
        print(arm, n, 'files')


if __name__ == '__main__':
    main()
