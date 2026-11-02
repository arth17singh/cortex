# CORTEX `memory/LEDGER.md` template (v4)

Write everything between the `=====` lines to `memory/LEDGER.md`. Keep exactly one row per chat (top-level transcript). `scripts/ledger_scan.py` parses the table, so keep the column order. The first cell must be the full transcript id in backticks.

=====
# CORTEX ledger: what has been tracked

The only record of which transcript lines are already in memory. `/cortex all` and recovery process only what's missing. Lines are 1-based, as in `wc -l`. Check it with `python3 ~/.claude/skills/cortex/scripts/ledger_scan.py <project> --current <id>`.

**States:**
- `live`: being recorded as the chat runs.
- `mined`: backfilled.
- `partial`: some ranges are still uncovered.
- `excluded`: never read, quoted or logged.
- `untracked`: not yet processed.

**Range kinds** (separated by `;`, with plain hyphens):
- `mined a-b`
- `live a-b`: the end is bumped on every log append.
- `skipped a-b`: deliberately left out.
- `paused a-b`: an open end `a-` means still paused.

| Chat | Dates (local) | State | Ranges | Session logs | Notes |
|---|---|---|---|---|---|
| `<full-transcript-id>` | YYYY-MM-DD – MM-DD | <state> | <ranges> | <log filenames> | <one-line topic> |
=====

## Editing rules
- **Only mark lines you actually logged.** Hooks and scripts never move ranges; Claude does, right after appending to the session log.
- **Never shrink a range**, except with `/cortex exclude` (ranges become `none`). `/cortex forget` changes memory, not the ledger. `/cortex include` removes `excluded`, `skipped` or `paused` markings, turning them back into gaps.
- **Never extend a `live` range across a pause.** Resume starts a new `live` segment.
- **Re-read the ledger right before every edit;** another chat may have changed it.
