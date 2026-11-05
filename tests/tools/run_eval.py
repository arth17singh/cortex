#!/usr/bin/env python3
"""Run the blind question set against one memory-system arm (one fresh `claude -p` per question).

usage: run_eval.py --arm DIR --name NAME --questions questions.json --out tests/results/<date>/<name>/
                   [--ids R01,R02] [--workers 4] [--model sonnet] [--timeout 300]
                   [--disallow Edit,Write,MultiEdit] [--force]

Each question runs from cwd = the arm folder with only the arm's project settings/hooks
(`--setting-sources project`), no session persistence, write tools disallowed, stdin /dev/null.
CLAUDE_PROJECT_DIR and CORTEX_NESTED are removed from the child env (the arm's hooks must run).
Writes per question <id>.stream.jsonl (raw stream-json transcript, incl. tool calls) and <id>.json
(answer, timing, cost, usage; never the expected answer), plus run_meta.json. Resumable: ids whose
<id>.json exists with error == null are skipped.
"""
import argparse, datetime, json, os, shutil, signal, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MEMORY_FILES = ('CLAUDE.md', 'CLAUDE.local.md', '.claude/settings.json', '.claude/settings.local.json')
PRINT_LOCK = threading.Lock()


def log(msg):
    with PRINT_LOCK:
        print(msg, flush=True)


def now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def atomic_json(path, obj):
    tmp = path.with_suffix(path.suffix + '.%d.tmp' % os.getpid())
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)


def ancestor_leaks(arm):
    """Memory/settings files in parent dirs of the arm: Claude Code walks up from cwd and would load them."""
    hits = []
    for d in arm.parents:
        hits += [str(d / f) for f in MEMORY_FILES if (d / f).exists()]
    home_claude = Path.home() / '.claude'
    return [h for h in hits if not h.startswith(str(home_claude))]


def arm_settings(arm):
    """(allow list, env) from the arm's .claude/settings.json. Claude Code ignores a project's permissions.allow in an
    untrusted folder under -p, so the runner passes them as --allowedTools and the env into the child process."""
    try:
        s = json.loads((Path(arm) / '.claude' / 'settings.json').read_text())
    except (OSError, ValueError):
        return [], {}
    return list((s.get('permissions') or {}).get('allow') or []), dict(s.get('env') or {})


def child_env(extra=None):
    env = dict(os.environ)
    env.update(extra or {})
    for k in ('CLAUDE_PROJECT_DIR', 'CORTEX_NESTED'):
        env.pop(k, None)
    env['CLAUDE_CODE_DISABLE_AUTO_MEMORY'] = '1'   # no cross-question leakage via auto memory
    return env


def command(args, question, allow=(), mcp=None):
    """Only the arm's own MCP servers (--strict-mcp-config + the arm's .mcp.json), no web tools: answers come from
    the arm's files and memory tools only."""
    return (['claude', '-p', '--model', args.model, '--setting-sources', 'project', '--strict-mcp-config']
            + (['--mcp-config', mcp] if mcp else [])
            + ['--no-session-persistence', '--disallowedTools=' + args.disallow]
            + (['--allowedTools', *allow] if allow else [])
            + ['--output-format', 'stream-json', '--verbose', '--', question])


def parse_stream(path):
    """Last `result` event of a stream-json transcript (or None)."""
    result = None
    try:
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip()
            if not line.startswith('{'):
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get('type') == 'result':
                result = ev
    except OSError:
        pass
    return result


def done(out, qid):
    p = out / (qid + '.json')
    try:
        return json.loads(p.read_text(encoding='utf-8')).get('error') is None
    except (OSError, ValueError):
        return False


def run_one(q, args, arm, out):
    qid = q['id']
    stream = out / (qid + '.stream.jsonl')
    rec = {'id': qid, 'category': q['category'], 'question': q['question'], 'answer': None,
           'duration_ms': None, 'wall_ms': None, 'cost_usd': None, 'usage': None, 'num_turns': None,
           'exit_code': None, 'error': None}
    t0 = datetime.datetime.now()
    with open(stream, 'wb') as fh:
        allow, extra_env = arm_settings(arm)
        mcp = str(Path(arm) / '.mcp.json') if (Path(arm) / '.mcp.json').exists() else None
        proc = subprocess.Popen(command(args, q['question'], allow, mcp), cwd=str(arm), env=child_env(extra_env),
                                stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.PIPE,
                                start_new_session=True)
        try:
            _, err = proc.communicate(timeout=args.timeout)
            rec['exit_code'] = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            _, err = proc.communicate()
            rec['exit_code'] = proc.returncode
            rec['error'] = 'timeout after %ss' % args.timeout
    rec['wall_ms'] = int((datetime.datetime.now() - t0).total_seconds() * 1000)
    res = parse_stream(stream)
    if res:
        u = res.get('usage') or {}
        rec.update(answer=res.get('result'), duration_ms=res.get('duration_ms'),
                   cost_usd=res.get('total_cost_usd'), num_turns=res.get('num_turns'),
                   usage={k: u.get(k, 0) for k in ('input_tokens', 'output_tokens',
                                                   'cache_creation_input_tokens', 'cache_read_input_tokens')})
        if rec['error'] is None and (res.get('is_error') or res.get('subtype') != 'success'):
            rec['error'] = 'result %s: %s' % (res.get('subtype'), str(res.get('result'))[:300])
    elif rec['error'] is None:
        rec['error'] = 'no result event'
    if rec['error'] is None and rec['exit_code'] != 0:
        rec['error'] = 'exit %s' % rec['exit_code']
    if rec['error'] and err:
        rec['stderr'] = err.decode('utf-8', 'replace')[-2000:]
    atomic_json(out / (qid + '.json'), rec)
    log('%s  %s  %.1fs  $%s' % (qid, 'ERROR ' + rec['error'] if rec['error'] else 'ok',
                                rec['wall_ms'] / 1000.0, rec['cost_usd']))
    return rec


def git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(Path(__file__).resolve().parent),
                                       stderr=subprocess.DEVNULL).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--arm', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--questions', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--ids', default='')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--model', default='sonnet')
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--disallow', default='Edit,Write,MultiEdit,NotebookEdit,WebSearch,WebFetch')
    ap.add_argument('--force', action='store_true', help='run even if parent dirs hold CLAUDE.md/settings')
    args = ap.parse_args()

    arm = Path(args.arm).resolve()
    if not arm.is_dir():
        sys.exit('arm folder not found: %s' % arm)
    leaks = ancestor_leaks(arm)
    if leaks and not args.force:
        sys.exit('refusing: parent dirs of the arm hold memory/settings files that would load:\n  '
                 + '\n  '.join(leaks) + '\n(move the arm or pass --force)')
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    qs = json.loads(Path(args.questions).read_text(encoding='utf-8'))
    if args.ids:
        want = set(i.strip() for i in args.ids.split(',') if i.strip())
        qs = [q for q in qs if q['id'] in want]
    todo = [q for q in qs if not done(out, q['id'])]
    log('%s: %d questions, %d already done, %d to run' % (args.name, len(qs), len(qs) - len(todo), len(todo)))

    meta_path = out / 'run_meta.json'
    try:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        meta = {'runs': []}
    try:
        version = subprocess.check_output(['claude', '--version'], stdin=subprocess.DEVNULL).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        version = None
    run = {'name': args.name, 'arm': str(arm), 'cwd': str(arm), 'model': args.model,
           'claude_version': version, 'claude_path': shutil.which('claude'), 'git_commit': git_commit(),
           'questions': str(Path(args.questions).resolve()), 'ids_run': [q['id'] for q in todo],
           'workers': args.workers, 'timeout_s': args.timeout,
           'flags': command(args, '<question>', arm_settings(arm)[0])[1:], 'env': arm_settings(arm)[1], 'parent_leaks_forced': leaks,
           'start': now(), 'end': None}
    meta['runs'].append(run)
    atomic_json(meta_path, meta)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        recs = list(ex.map(lambda q: run_one(q, args, arm, out), todo))
    run['end'] = now()
    run['errors'] = [r['id'] for r in recs if r['error']]
    atomic_json(meta_path, meta)
    log('done: %d ok, %d errors' % (len(recs) - len(run['errors']), len(run['errors'])))


if __name__ == '__main__':
    main()
