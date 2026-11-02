<!-- CORTEX rules v5.0 · master copy: reference/rules.md in the skill · /cortex upgrade refreshes memory/RULES.md -->
# CORTEX memory rules

Memory lives in `memory/`. `<skill>` is the skill path in the CORTEX heading of `CLAUDE.md`. Commands: `/cortex help`.
- **L0** (always loaded): these rules, `INDEX.md` (status, and the map of every topic file and recent session log), `team/user-preferences.md`.
- **L1** `memory/<topic>/*.md`: current truth, under ~150 lines each.
- **L2** `memory/sessions/*.md`: per-chat history (older logs are mapped in `sessions/README.md`), plus `log/changelog.md`, the repo docs and the code.
- **On demand only:** raw chats, `LEDGER.md` (coverage), `PROTOCOL.md` (config, caps, consolidation, audit), `_templates/`.

## Start
- **Recording mode** is the index's `Recording:` value. `auto`: this chat records. `manual`: it records only if its ledger row has an open `live` range. `paused`: nothing is written; remind the user once.
- **Recovery:** a `CORTEX:` line at the top (from the SessionStart hook) gives this chat's id, transcript and any unlogged tails in other chats. Recover those first with the extractor command it names: append to that chat's session log and extend its ledger range. Never touch chats flagged active.
- **Off limits:** never read chats or ranges the ledger marks `excluded`, `skipped` or `paused`.

## Reading
- **Check before acting.** Before editing code, stating a fact about the project, or recommending an option, read the L1 file the map routes it to, and grep the session logs for earlier rejections (`grep -n -i -E 'rejected|<term>' memory/sessions/*.md`). Never re-propose a rejected option without saying it was rejected, and why.
- **Pick files** from the map: the 1–3 L1 files whose nouns or triggers fit. Check the `Summary:` line (`head -4`) before reading a whole file. L1 files are read whole.
- **Session logs and the changelog are never read whole:** `grep -n -i '<term>' memory/sessions/*.md memory/log/*.md`, then read about ±25 lines around the hits. The map says which log covers what: the newest logs have their own line; older ones are in week and month lines (follow them to `sessions/README.md` for the per-log line), and big folders in a summary line (follow it to that folder's `_index.md`).
- **Which layer answers what:**
  - "What's true now, how do I run it" → L1.
  - "Why, who said what, exact wording, what was rejected" → session log.
  - "What changed recently" → changelog.
  - "What the code does" → the code.
- **Raw chats are the last resort:** `python3 <skill>/scripts/ledger_scan.py <project> --grep '<term>'`, then `extract_transcript.py` on a ±20-line window. Never grep the `.jsonl` directly; that ignores exclusions.
- **Stop** when answered. Verify facts about the system with a read-only check of the code. Read at most 4 memory files beyond L0 per question (one grep across many logs counts as one read); if you needed more, add the missing nouns to the map.
- **Trust order:** code, then the user's latest explicit statement, then a sourced L1 bullet, then an unsourced or "not yet verified" bullet, then a session log, then a compaction summary. Say what you relied on when it matters, and cite `memory/<file>:<line>` or `(<id8> L<line>)`.
- **On a conflict,** act on the trust order, fix the stale file in the same turn, and add a changelog line.
- **Don't re-read L0,** except `INDEX.md` right before rewriting it while another chat is live (see the ledger): it may have changed.

## Writing (only while recording; in the same turn, never only at the end)
**Storage test:** "Would a future session be better informed, decide better, or answer better for having this?"
- If yes, store it, even if it fits no category; examples are in `PROTOCOL.md`.
- Subtle details (exact phrasing, caveats, numbers, quirks) go to the session log when in doubt.
- Drop noise. Work on the memory system itself gets one changelog line, not L1 or narrative.

**After each exchange that passes the test:**
1. **Session log** `memory/sessions/YYYY-MM-DD_<id8>-<topic>.md`. At the first such exchange: `cp memory/_templates/session.md <path>`, add this chat's ledger row and its line in the map. Each exchange heading ends with `(L<a>-<b>)`, the transcript lines it covers. Record every decision with its reason and every rejected alternative with why.
2. **Ledger, same turn:** set this chat's `live` end to the transcript's current `wc -l` (one edit). Never extend a live range across a pause; never mark lines you didn't log.
3. **L1, when current truth changes** (a decision, something built, fixed or renamed, a bug or lesson, a preference, a reusable explanation): edit the one L1 file that owns the fact, in place, with a source tag: `(<id8> L<line>)` for a chat, `(code: path:line)` when verified. No tag means unverified. A rejection also gets a bullet there: `Rejected: <option> (<why>) (<id8> L<line>)`.
4. **Map:** keep `INDEX.md` routing current: new nouns and triggers for the file you changed, and this chat's session-log line. Status and next steps go in "Where we are" (≤8 one-line bullets, each dated `(YYYY-MM-DD)` and linking its L1 file).
5. **Changelog:** a one-liner at notable events (≤120 chars, dated, with a source tag).

**Rules:**
- Every number, path and command lives in exactly one L1 file; others link to it.
- Absolute dates, in the timezone on the index's second line.
- How the user works → `team/user-preferences.md`, one line each (quotes go to the session log).
- Never store secrets, keys, tokens, passwords, or anyone's email or phone number (`[redacted]`).
- Never use Claude's auto-memory for project facts.

## Learning (memory improves itself)
- **When the user corrects you,** or says something memory should have known ("we already decided…", "no, it's…"), that is a recall miss. In the same turn (if recording is paused, write nothing: tell the user memory has it wrong and suggest `/cortex save <the fact>`):
  1. Fix the fact in its owning L1 file, with a source tag.
  2. Find why memory missed it, and fix that too: never stored → store it; stored but not reachable from the map → add its nouns to the map; stored in the wrong file → move it.
  3. Add a changelog line `recall miss: <topic> · fixed <what>`.
- **Self-test:** when the `CORTEX:` line says a self-test is due, run it as it says (`<skill>/reference/selftest.md`) without waiting to be asked.
- Learning edits memory only, never this file.

## Checkpoint (before pause, clear, switching chats, long work, or `/cortex save`)
1. Session log up to date: exchanges, decisions, rejected alternatives, open threads.
2. Ledger live end = current `wc -l` (skip if paused).
3. Affected L1 files and the map updated.
4. Index "Where we are" refreshed.
5. Say nothing about it, unless the user ran `/cortex save`; then confirm in one line.

## Budget
When the hook or `/cortex status` lists a consolidation reason (a map, rollup or preference cap exceeded, an old "Where we are" bullet, or memory over its ceiling), run "Consolidation" in `PROTOCOL.md` before other work. It moves detail one level down and leaves a pointer; it never deletes.

## Silent memory
Memory work is silent. Never say in a reply that you read, wrote, logged or checkpointed memory: no "Saved to memory", no "Session log: …", no `⟦CORTEX⟧` lines. The Stop hook already shows the user a `⟲ CORTEX synced` line naming what changed. Still say anything that needs the user's OK, the paused reminder, and the reply to a `/cortex` command the user ran. Citing memory as a source in an answer is fine (see Reading).

## Recall line (the one memory line you do write)
When an answer depends on something from memory that the user didn't say in this chat (a past decision, a rejected option, an old number or fact), end the reply with one line that shows what memory supplied and how much of it:
`<marker> recalled · <layers> · <scope> · <the gist>`
- **marker:** how much memory the answer drew on: `◈` one source, `◈◈` two or three, `◈◈◈` four or more (a source is one topic file, session log or raw chat you used).
- **layers:** the deepest layer you read, or a range when you used several: `L0` (always loaded), `L1` (topic file), `L2` (session log), `L3` (raw chat), e.g. `L1–L2`.
- **scope:** for one source, its age since it was decided or recorded (`today`, `3d`, `11w`, `5mo`); for several, how many and the span they cover (`6 sources · Aug–Oct`).
- **gist:** what memory contributed, at most 12 words for one source and 20 for several; a label, not a quote, since the detail belongs in the answer.
- **flags:** if a memory you relied on is `superseded` (name the old and the new: "Radar → in-house model"), `unverified` (no source tag and not checked in code) or `stale` (only a status, something in progress or temporary like "A/B running" or "blocked on review", recorded more than 14 days ago and not confirmed since; decisions, rejections and facts never go stale by age), add a second line for it alone, so the warning isn't buried: `◈ recalled · L1 · 6w · superseded · fraud scoring: Stripe Radar → in-house model`.
- If the user asks to see what was recalled, quote it with `file:line`.
- Never for preferences, these rules, or memory the answer didn't need. No file names. Examples: `◈ recalled · L2 · 12w · Kafka rejected as event bus: ops burden for a team of four` · `◈◈◈ recalled · L1–L2 · 6 sources · Aug–Oct · search: OpenSearch, 3 shards, 180 ms p99, BM25-only rejected`
