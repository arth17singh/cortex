#!/usr/bin/env python3
"""CORTEX transcript reader.

usage: extract_transcript.py <transcript.jsonl> <IANA_TZ> [first_line] [last_line]

Prints the readable text of a Claude Code transcript with 1-based line numbers (the same numbering
as `wc -l` and the ledger): user messages (including ones typed mid-turn and slash-command
arguments), assistant text, one line per tool call, subagent reports (truncated), and compaction
summaries (labelled). Tool payloads, system reminders and skill bodies are skipped. Common secret
formats are masked as [redacted]. Malformed lines are skipped, never fatal.
"""
import json, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

path, tz = sys.argv[1], ZoneInfo(sys.argv[2])
a = int(sys.argv[3]) if len(sys.argv) > 3 else 1
b = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
SKIP = ('<system-reminder>', 'Base directory for this skill', '<local-command', '<task-notification>')
SECRET = re.compile(r'AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_\w+'
                    r'|xox[abpr]-[\w-]+|AIza[0-9A-Za-z_-]{35}|eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]*'
                    r'|(?i:(?:secret|passw(?:or)?d|token|api[_-]?key|access[_-]?key)\w*\s*[=:]\s*)\S+'
                    r'|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')
red = lambda s: SECRET.sub('[redacted]', s)
agent_ids = set()

def when(ts):
    try: return datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(tz).strftime('%Y-%m-%d %H:%M')
    except (ValueError, AttributeError): return '?'

def command(txt):   # "<command-name>/x</command-name>...<command-args>y</command-args>" -> "/x y"
    n = re.search(r'<command-name>(.*?)</command-name>', txt, re.S)
    g = re.search(r'<command-args>(.*?)</command-args>', txt, re.S)
    return f"{n.group(1) if n else ''} {g.group(1) if g else ''}".strip() if n else None

with open(path, encoding='utf-8', errors='replace') as f:
    for n, line in enumerate(f, start=1):
        if n < a: continue
        if n > b: break
        try: d = json.loads(line)
        except ValueError: continue
        if not isinstance(d, dict): continue
        role, w = d.get('type'), when(d.get('timestamp') or '')
        if role == 'queue-operation' and d.get('operation') == 'enqueue' and isinstance(d.get('content'), str) \
                and not d['content'].lstrip().startswith(SKIP):
            who = 'AGENT REPORT' if d['content'].lstrip().startswith('<agent-message') else 'USER (sent mid-turn)'
            print(f'[L{n} {w} {who}] {red(d["content"].strip())}\n'); continue
        if role not in ('user', 'assistant') or not isinstance(d.get('message'), dict): continue
        c = d['message'].get('content')
        label = 'COMPACTION SUMMARY (lower trust)' if d.get('isCompactSummary') else role.upper()
        for bl in ([{'type': 'text', 'text': c}] if isinstance(c, str) else (c if isinstance(c, list) else [])):
            if isinstance(bl, str): bl = {'type': 'text', 'text': bl}
            if not isinstance(bl, dict): continue
            if bl.get('type') == 'text':
                txt = (bl.get('text') or '').strip()
                cmd = command(txt) if '<command-name>' in txt else None
                if cmd: print(f'[L{n} {w} USER COMMAND] {red(cmd)}\n')
                elif txt and not txt.startswith(SKIP) and not txt.startswith('<command-'):
                    print(f'[L{n} {w} {label}] {red(txt)}\n')
            elif bl.get('type') == 'tool_use':
                inp = bl.get('input') if isinstance(bl.get('input'), dict) else {}
                if bl.get('name') in ('Agent', 'Task'): agent_ids.add(bl.get('id'))
                key = inp.get('file_path') or inp.get('command') or inp.get('description') or inp.get('query') or ''
                print(f'[L{n} {w} TOOL {bl.get("name")}] {red(str(key)[:150])}')
            elif bl.get('type') == 'tool_result' and bl.get('tool_use_id') in agent_ids:
                rc = bl.get('content')
                txt = rc if isinstance(rc, str) else ' '.join(x.get('text', '') for x in (rc or []) if isinstance(x, dict))
                if txt.strip(): print(f'[L{n} {w} SUBAGENT REPORT] {red(txt.strip()[:3000])}\n')
