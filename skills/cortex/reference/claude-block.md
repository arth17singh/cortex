# CORTEX `CLAUDE.md` block (v4)

Insert everything between the two `=====` lines into the project's `CLAUDE.md`, verbatim. Replace every `{{…}}` and leave `<…>` patterns literal. On upgrade, replace everything from `<!-- CORTEX:BEGIN` to `<!-- CORTEX:END -->`. Re-fill the `{{…}}` values from the old block, and move any project-specific lines added inside the old block to the project's own rules section.

**Placeholders:**
- `{{TOPIC_ROUTING}}`: one line listing topic folders with what goes in each, e.g. `` `hackathon/` event and research · `product/` concept, demo, explanations · `engineering/` code, running, gaps ``.
- `{{IANA_TZ}}`

=====
<!-- CORTEX:BEGIN v4 -->
## Project memory (CORTEX)

Always loaded: @memory/INDEX.md @memory/team/user-preferences.md

Memory lives in `memory/`.
- **L0** (above): status, a map of every file, and how the user works.
- **L1** `memory/<topic>/*.md`: current truth, under ~150 lines each.
- **L2** `memory/sessions/*.md`: per-chat history, plus the repo docs and code.
- Raw chats, the ledger of what's covered (`LEDGER.md`), templates and config (`PROTOCOL.md`) are used only when a step below says so.

Commands: `/cortex help`. A `CORTEX:` line at the top of the context (from the SessionStart hook) gives this chat's id, transcript path, recording mode, and any gaps to recover.

### 1. Start
- **Recording mode** (index "Recording" line):
  - `auto`: this chat records;
  - `manual`: it records only if its ledger row has an open `live` range;
  - `paused`: nothing is written. Remind the user once.
- **Recovery:** if the CORTEX line lists unlogged tails, recover them first. Use `python3 ~/.claude/skills/cortex/scripts/extract_transcript.py <file> {{IANA_TZ}} <a> <b>`, append to that chat's session log, and extend its ledger range. Never touch chats flagged active.
- **Off limits:** never read chats or ranges the ledger marks `excluded`, `skipped` or `paused`.

### 2. Reading memory
- **Pick files:** from the index table, pick the 1–3 L1 files whose "Load when" fits. Check the `Summary:` line (`head -4`) before reading a whole file.
- **L1 files** are read whole. **Session logs and the changelog** are never read whole: `grep -n -i '<term>' memory/sessions/*.md memory/log/*.md`, then read about ±25 lines around the hits.
- **Which layer answers what:**
  - "What's true now, how do I run it" → L1.
  - "Why, who said what, exact wording, what was rejected" → session log.
  - "What changed recently" → changelog.
  - "What the code does" → the code.
- **Raw chats are the last resort:** `python3 ~/.claude/skills/cortex/scripts/ledger_scan.py <project> --grep '<term>'`, then the extractor on a ±20-line window. Never grep the `.jsonl` directly; that ignores exclusions.
- **Stop** when answered. Verify facts about the system with a read-only check of the code. Read at most 4 memory files beyond L0; if you needed more, fix the index entry.
- **Trust order:** code, then the user's latest explicit statement, then a sourced L1 bullet, then an unsourced or "not yet verified" bullet, then a session log, then a compaction summary. Say what you relied on when it matters, and cite `memory/<file>:<line>` or `(e016c8fe L2104)`.
- **On a conflict,** act on the trust order, fix the stale file in the same turn, and add a changelog line.
- **Don't re-read L0;** it's already loaded.

### 3. Writing (only while recording; in the same turn, never only at the end)
**Test:** "Would a future session be better informed, decide better, or answer better for having this?"
- If yes, store it, even if it fits no category; examples are in `PROTOCOL.md`.
- Subtle details (exact phrasing, caveats, numbers, quirks) go to the session log when in doubt.
- Drop noise.
- Work on the memory system itself gets one changelog line, not L1 or narrative.

**After each exchange that passes the test:**
1. Append to this chat's session log (`memory/sessions/YYYY-MM-DD_<8-char chat id>-<topic>.md`).
   - At the first such exchange, create it with `cp memory/_templates/session.md <path>`, add this chat's ledger row, and tell the user "Session log: `<path>`".
   - Each exchange heading ends with `(L<a>-<b>)`, the transcript lines it covers.
2. In the same turn, set this chat's ledger `live` end to the transcript's current `wc -l` (one edit). The ledger is the only record of coverage. Never extend a live range across a pause; never mark lines you didn't log.
3. When current truth changes (a decision, something built, fixed or renamed, a bug or lesson, a preference, a reusable explanation), also edit the one L1 file that owns that fact. Add a source tag: `(e016c8fe L2104)` for a chat, or `(code: path:line)` when verified. No tag means unverified.
4. At notable events, add a changelog one-liner (≤120 chars, dated, with a source tag).

**Where things go:**
- {{TOPIC_ROUTING}}
- How the user works → `team/user-preferences.md` (one line each; quotes go to the session log).
- Status and next steps → "Where we are" in the index (≤8 one-line bullets, each linking its L1 file).

**Rules:**
- Every number, path and command lives in exactly one L1 file; others link to it.
- Edit in place.
- Absolute dates ({{IANA_TZ}}).
- Never store secrets, keys, tokens, passwords, or anyone's email or phone number (`[redacted]`).
- Never use Claude's auto-memory for project facts.

### 4. Checkpoint (before pause, clear, switching chats, long work, or `/cortex save`)
1. Session log up to date: exchanges, decisions, open threads.
2. Ledger live end = current `wc -l` (skip if paused).
3. Affected L1 files updated.
4. Index "Where we are" refreshed.
5. Tell the user.

### 5. Telemetry (so the user can see CORTEX working)
Unless the index says `Logs: off`, print one short line, in this format, after each memory action. Log only what you actually did; never log an action you skipped.
- Read: `⟦CORTEX⟧ recall ▸ L1 <topic>/<file>.md · <n> lines · trust: <code|user|sourced L1|session log>`
- Write: `⟦CORTEX⟧ commit ▸ L2 <session log> (L<a>-<b>) + L1 <file> · ledger live → <n>`
- Recovery: `⟦CORTEX⟧ recover ▸ <id8> L<a>-<b> → <session log>`
- Checkpoint: `⟦CORTEX⟧ checkpoint ▸ ledger live → <n> · L1 <k> files touched · index refreshed`
Keep it to one line per action, with no commentary.

Caps, rollovers, templates and the audit are in `PROTOCOL.md`.
<!-- CORTEX:END -->
=====
