#!/usr/bin/env python3
"""Convert SpecStory chat histories (.specstory/history/*.md, Markdown v1 and v2) into Claude Code-style JSONL
transcripts, one file per session, so the CORTEX pipeline (archive, index, backfill) runs on them unchanged.

usage: specstory_to_jsonl.py <specstory dir> <out dir>

Per session: user and agent turns become `user` / `assistant` lines with timestamps (from the turn header, else the
file name, +1 s per turn); `<tool-use ...>` blocks become `tool_use` content blocks (name, a one-line description,
and the command or path); tool output and thinking blocks are dropped, as extract_transcript.py drops them for real
transcripts. The session id comes from the SpecStory header when present, else from the file name.
"""
import json, re, sys, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

HEAD = re.compile(r'^_\*\*(User|Assistant|Agent)(?:\s*\(([^)]*)\))?\*\*_\s*$', re.M)
TOOL = re.compile(r'<tool-use\b[^>]*?data-tool-name="([^"]*)"[^>]*>(.*?)</tool-use>', re.S)
THINK = re.compile(r'<think>.*?</think>|<details>\s*<summary>\s*Thought[^<]*</summary>.*?</details>', re.S)
TS = re.compile(r'(\d{4}-\d{2}-\d{2})[ T_](\d{2})[:-](\d{2})(?:[:-](\d{2}))?')


def parse_ts(s):
    m = TS.search(s or '')
    if not m:
        return None
    d, hh, mm, ss = m.group(1), m.group(2), m.group(3), m.group(4) or '00'
    return datetime.strptime(f'{d} {hh}:{mm}:{ss}', '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)


def tool_block(name, body):
    body = re.sub(r'```.*?```', '', body, flags=re.S)                     # tool output
    body = re.sub(r'</?(details|summary)>', '\n', body)
    lines = [l.strip() for l in body.split('\n') if l.strip() and not l.strip().startswith('Tool use:')]
    cmd = next((re.sub(r'^`|`$', '', l) for l in lines if l.startswith('`') and l.endswith('`')), '')
    desc = next((l for l in lines if not l.startswith('`')), '')
    inp = {'description': desc[:200]}
    if cmd:
        inp['command' if name.lower() in ('bash', 'shell', 'run_terminal_cmd') else 'file_path'] = cmd[:300]
    return {'type': 'tool_use', 'id': 'toolu_' + uuid.uuid4().hex[:20], 'name': name, 'input': inp}


def convert(md_path, out_dir):
    text = md_path.read_text(encoding='utf-8', errors='replace')
    sid_m = re.search(r'Session ([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', text)
    sid = sid_m.group(1) if sid_m else str(uuid.uuid5(uuid.NAMESPACE_URL, md_path.name))
    t0 = parse_ts(md_path.name) or parse_ts(text[:400]) or datetime(2025, 1, 1, tzinfo=timezone.utc)
    heads = list(HEAD.finditer(text))
    rows, t = [], t0
    for k, h in enumerate(heads):
        body = text[h.end(): heads[k + 1].start() if k + 1 < len(heads) else len(text)]
        body = re.sub(r'^\s*---\s*$', '', body, flags=re.M).strip()
        ts = parse_ts(h.group(2) or '')
        t = ts if ts and ts >= t else t + timedelta(seconds=1)
        role = 'user' if h.group(1) == 'User' else 'assistant'
        body = THINK.sub('', body)
        blocks, pos = [], 0
        for m in TOOL.finditer(body):
            pre = body[pos:m.start()].strip()
            if pre:
                blocks.append({'type': 'text', 'text': pre})
            blocks.append(tool_block(m.group(1), m.group(2)))
            pos = m.end()
        rest = re.sub(r'<[^>]+>', '', body[pos:]).strip()
        if rest:
            blocks.append({'type': 'text', 'text': rest})
        if not blocks:
            continue
        if role == 'user':
            content = ' '.join(b['text'] for b in blocks if b['type'] == 'text')
            if not content.strip():
                continue
            msg = {'role': 'user', 'content': content}
        else:
            msg = {'role': 'assistant', 'content': blocks}
        rows.append({'type': role, 'sessionId': sid, 'timestamp': t.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                     'uuid': str(uuid.uuid4()), 'message': msg})
    out = Path(out_dir) / f'{sid}.jsonl'
    with open(out, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return sid, len(rows)


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for md in sorted(src.glob('*.md')):
        sid, k = convert(md, dst)
        n += k
        print(f'{md.name[:60]:60s} -> {sid[:8]}  {k} lines')
    print(f'total {n} lines')


if __name__ == '__main__':
    main()
