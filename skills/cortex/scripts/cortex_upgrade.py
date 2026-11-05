#!/usr/bin/env python3
"""CORTEX upgrade to v8 for one project (what `/cortex upgrade` runs on a v5 or v7 project).

usage: cortex_upgrade.py <project_dir> [--tz IANA] [--transcripts DIR] [--dry-run] [--workers N]

1. Lists the project's chats with ledger_scan.py: excluded chats are skipped, skipped and paused ranges are never
   read (a chat open in another window is read up to now; records are deduplicated).
2. Backs up memory/ to memory/.backups/<YYYY-MM-DD-HHMM>-pre-v7/ (everything except older backups).
3. Backfills records from the transcripts (cortex_backfill.py: Haiku extraction, provenance `transcript`).
4. Archives every recorded chat into memory/chats/ (redacted, line-addressed; same exclusions) and builds the
   search index (memory/.cache/index.sqlite). A v7 project skips step 3 (it already has records).
5. Installs the v8 rules (memory/RULES.md) and the v8 CLAUDE.md block, and renders
   GRAPH.md and entities.md. Curated files (INDEX.md, topic files, session logs) are not touched.
--dry-run prints the plan (chats, lines, estimated model calls) and changes nothing.
"""
import argparse, json, re, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
import cortex_lib as L  # noqa: E402


def tz_of(root):
    m = re.search(r'\b([A-Z][a-z]+/[A-Za-z_]+(?:/[A-Za-z_]+)?)\b', '\n'.join(
        (root / 'memory' / 'INDEX.md').read_text(encoding='utf-8', errors='replace').splitlines()[:4]))
    return m.group(1) if m else 'UTC'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--tz')
    ap.add_argument('--transcripts')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    root = L.find_root(a.project, explicit=True)
    if not root:
        sys.exit('no CORTEX memory here (memory/INDEX.md not found)')
    block = (root / 'CLAUDE.md').read_text(encoding='utf-8', errors='replace') if (root / 'CLAUDE.md').exists() else ''
    if '<!-- CORTEX:BEGIN v8' in block:
        print(json.dumps({'status': 'already v8', 'project': str(root)}))
        return
    from_v7 = '<!-- CORTEX:BEGIN v7' in block
    tz = a.tz or tz_of(root)
    scan_args = [sys.executable, str(HERE / 'ledger_scan.py'), str(root), '--json']
    if a.transcripts:
        scan_args += ['--transcripts', a.transcripts]
    scan = json.loads(subprocess.run(scan_args, capture_output=True, text=True).stdout or '{}')
    files, blocks, plan = [], [], []
    for c in scan.get('chats', []):
        skip = c['state'] == 'excluded'
        br = [] if skip else L.blocked_ranges(c.get('ranges'), c['lines'])
        plan.append({'chat': c['short'], 'lines': c['lines'], 'use': not skip, 'never_read': br})
        if not skip:
            files.append(str(Path(scan['transcripts']) / (c['id'] + '.jsonl')))
            blocks += [f"{c['short']}:{x}-{y}" for x, y in br]
    lines = sum(p['lines'] for p in plan if p['use'])
    summary = {'project': str(root), 'tz': tz, 'transcripts': scan.get('transcripts'), 'chats': plan,
               'lines_to_read': lines, 'est_model_calls': max(1, lines // 100) + 1, 'warnings': scan.get('warnings', [])}
    if a.dry_run:
        print(json.dumps(dict(summary, status='dry run: nothing changed'), indent=1))
        return
    if not files:
        sys.exit('no transcripts found for this project; nothing to backfill (see warnings with --dry-run)')

    mem = root / 'memory'
    backup = mem / '.backups' / (datetime.now().strftime('%Y-%m-%d-%H%M') + '-pre-v7')
    shutil.copytree(mem, backup, ignore=lambda d, names: ['.backups'] if Path(d) == mem else [])
    if from_v7:
        bf, stats = subprocess.CompletedProcess([], 0), '{"skipped": "v7 project already has records"}'
    else:
        bf = subprocess.run([sys.executable, str(HERE / 'cortex_backfill.py'), *files, '--root', str(root), '--tz', tz,
                             '--workers', str(a.workers), *sum((['--block', b] for b in blocks), [])],
                            capture_output=True, text=True)
        stats = (bf.stdout.strip().splitlines() or ['{}'])[-1]
    arc_args = [sys.executable, str(HERE / 'cortex_archive.py'), '--root', str(root), '--all', '--index', '--tz', tz]
    if a.transcripts:
        arc_args += ['--transcripts', a.transcripts]
    arc = subprocess.run(arc_args, capture_output=True, text=True)

    shutil.copy(SKILL / 'reference' / 'rules.md', mem / 'RULES.md')
    stub = re.search(r'=====\n(<!-- CORTEX:BEGIN v8 -->.*?<!-- CORTEX:END -->)\n=====',
                     (SKILL / 'reference' / 'claude-block.md').read_text(), re.S).group(1).replace('{{SKILL_DIR}}', str(SKILL))
    md_path = root / 'CLAUDE.md'
    md = md_path.read_text(encoding='utf-8')
    new = re.sub(r'<!-- CORTEX:BEGIN.*?<!-- CORTEX:END -->', lambda m: stub, md, count=1, flags=re.S)
    md_path.write_text(new if new != md else md.rstrip() + '\n\n' + stub + '\n', encoding='utf-8')
    import cortex_render
    cortex_render.render(root)
    try:
        archived = json.loads((arc.stdout.strip().splitlines() or ['{}'])[-1])
    except ValueError:
        archived = {'error': (arc.stdout + arc.stderr)[-300:]}
    print(json.dumps(dict(summary, status='upgraded to v8', backup=str(backup), backfill=json.loads(stats)
                          if stats.startswith('{') else stats[-300:], backfill_exit=bf.returncode, archive=archived,
                          next='register the memory tools once: claude mcp add --scope user cortex -- python3 '
                               + str(HERE / 'cortex_mcp.py')), indent=1))


if __name__ == '__main__':
    main()
