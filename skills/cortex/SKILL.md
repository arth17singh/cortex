---
name: cortex
description: "CORTEX: layered, self-maintaining project memory. Subcommands: start (record from now), all (backfill untracked past chats), status, save, pause/resume, exclude/include, forget, recall, audit, config, help. Use when the user runs /cortex."
argument-hint: "help | start [--from-chat-start] | all [only <chat>] [since DATE] [last N] [exclude X] [include-skipped] [--yes] | status | save [note] | pause [--project] | resume [--project] | exclude <chat> | include <chat> | forget <topic> | recall <question> | audit | config [key=value]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ledger_scan.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/extract_transcript.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/cortex_status.py *)
---

# CORTEX (v4)

**Request:** `/cortex $ARGUMENTS`
- **This chat:** session `${CLAUDE_SESSION_ID}` (short id = its first 8 characters). Find its transcript with `ls ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/*/${CLAUDE_SESSION_ID}.jsonl`.
- **Project:** `${CLAUDE_PROJECT_DIR}`. All `memory/` paths are relative to it.
- **Skill files:** `${CLAUDE_SKILL_DIR}`.

Read the first word of the request as the subcommand. If it's empty or unknown, run **help**.

## Rules for every subcommand
- **The user has full control.** Before anything that reads many chats, deletes memory, or changes git, hooks or recording settings, show exactly what will happen and wait for an OK (`--yes` skips this).
- **`memory/LEDGER.md` is the only coverage record.**
  - Mark only lines that were actually logged.
  - Never read or store `excluded` chats, or `skipped`/`paused` ranges, unless the user includes them.
  - Update the ledger in the same step as the memory it describes.
- **Line numbers** are 1-based, as in `wc -l`.
- **Tools:**
  - **Coverage:** `python3 ${CLAUDE_SKILL_DIR}/scripts/ledger_scan.py "${CLAUDE_PROJECT_DIR}" --current ${CLAUDE_SESSION_ID} --tz <IANA_TZ> [--preview] [--json] [--include-skipped]`. Each chat's **`backfill`** list is the work to do. `gaps` also includes this chat's live tail and chats flagged `active` (open elsewhere), which are never mined. Act on the scanner's warnings.
  - **Read a chat:** `python3 ${CLAUDE_SKILL_DIR}/scripts/extract_transcript.py <jsonl> <IANA_TZ> [from] [to]`. Measure with `| wc -c` before reading.
  - **Search chats:** `ledger_scan.py ... --grep '<regex>'`, which skips excluded, skipped and paused ranges. Never grep the transcript folder directly, and never read raw transcripts whole.
- **Privacy:** never store secrets, keys, tokens, passwords, or anyone's email or phone number (`[redacted]`). Never open `.env*` or credential files.
- **Storage test:** "would a future session be better informed for having this?"
  - Subtle details go to the session log; L1 stays lean, with source tags.
  - Drop noise, including narrative about the memory system itself.
- **Missing memory:** if `memory/INDEX.md` doesn't exist, every subcommand except help, status and config offers `start` (no history) or `all` (with history) first.
- **Day-to-day rules** are the `CLAUDE.md` block (`${CLAUDE_SKILL_DIR}/reference/claude-block.md`). Conventions, caps and the audit are in `memory/PROTOCOL.md`.

## Subcommands

### help
List the subcommands with one-line descriptions and two examples. If memory exists, add a 3-line status: recording mode, `backfill` line count, and whether hooks are installed.

### start [--from-chat-start]
Record **this chat from now on**; no past chats are read.
1. **If `memory/INDEX.md` is missing:** follow `${CLAUDE_SKILL_DIR}/reference/build.md` with **scope = none**. It builds from docs and code, installs the `CLAUDE.md` block, and asks about the recording mode, hooks and the commit setting.
2. **This chat's ledger row:**
   - If it exists, never relabel its ranges. Open `live <now>-<now>`, or report "already recording" if a live range is open with no open pause.
   - If it's new, write `skipped 1-<now-1>; live <now>-<now>`.
   - With `--from-chat-start`, capture lines 1..now-1 into the log first and write `live 1-<now>`.
3. **Session log:** create it if missing (`cp memory/_templates/session.md memory/sessions/<date>_<id8>-<topic>.md`) and announce "Session log: `<path>`".
4. **Confirm:** "Recording this chat from line <now>. Recording mode for new chats: <mode>. Hooks: <installed or not>."

### all [only <chat>] [since YYYY-MM-DD] [last N] [exclude <ids|dates|description>] [include-skipped] [--yes]
**Backfill every past chat that isn't tracked yet.** It's safe to re-run: it processes only `backfill` ranges.
1. Run the scanner with `--preview` (and `--include-skipped` if that option is given).
2. **Candidates:** each chat's `backfill`, filtered by the options and the default exclusions in `PROTOCOL.md`.
   - `since` and `exclude <date>` match a chat's first local date; `last N` means the most recently active chats.
   - Label chats that never recorded (manual mode or paused) as such.
   - List chats flagged `active` as "deferred: open in another chat".
3. **If there's nothing to do,** say so and stop.
4. **Otherwise show the plan:** chats and ranges with dates, previews and an estimate (`wc -c` ÷ 4); what's excluded, skipped or deferred; and what's already tracked. Wait for an OK unless `--yes`.
5. Follow `build.md` Steps 0–9, with Step 3 for the confirmed ranges. Integrate L1 updates and update the ledger per chat.
6. **This chat's row:** keep existing ranges and only open or extend `live` from <now>. If there's no row, write `skipped 1-<now-1>; live <now>-<now>`. If the user wants the whole chat, capture 1..now-1 first and write `live 1-<now>`.

### status
Read-only. Run:
`python3 ${CLAUDE_SKILL_DIR}/scripts/cortex_status.py "${CLAUDE_PROJECT_DIR}" --session ${CLAUDE_SESSION_ID}`

Your entire reply is its output, verbatim, in one code block. Write nothing before or after it: no preamble, no commentary, no settings recap, no suggestions. The dashboard already covers settings, warnings and the next action.

### save [note]
- **With no note:** run a full checkpoint (§4 of the `CLAUDE.md` block).
- **With a note:** store it in its owning L1 file, with a source tag, and in the session log, even if this chat is paused. Confirm where it went.

### pause [--project]
- **This chat (default):** set its current `live` end to <now-1> and add `paused <now>-`. Write nothing else from this chat except `/cortex save <note>`. Confirm: "Paused at line <now>. Other and future chats are unaffected."
- **`--project`:** set the index line to `Recording: paused (was <mode>) since <YYYY-MM-DD HH:MM>`, add `paused <now>-` to every row with an open live range (`<now>` = that chat's `wc -l`), then confirm. New chats in this project don't record; reading still works.

### resume [--project]
- **This chat:** close the pause as `paused <a>-<now-1>` and append a new segment `live <now>-<now>`. Never extend a live range across a pause.
- **`--project`:** restore the `was <mode>` value and close open pauses at each chat's current `wc -l`.

### exclude <chat>
Permanently leave a chat out of memory. The chat can be named by id prefix, date, or description.
1. **Identify it:** IDs and dates from the scanner. For a description, compare only the first-message previews. If it's ambiguous, list the candidates and ask.
2. **Mark it:** set its row to `excluded` with ranges `none`; this is the only operation allowed to shrink ranges. If it's this chat, stop recording now.
3. **If it was already in memory,** show its session logs and every L1 bullet tagged with its id (plus anything else that grep finds for distinctive terms from its logs). Offer to purge. On OK, delete them and add a changelog line without the content.

### include <chat>
- **Excluded chat:** set it to `untracked` with no ranges.
- **Skipped or paused part:** delete that range.

Then offer `/cortex all only <chat>`.

### forget <topic>
1. Search `memory/` for the topic.
2. Show every match with its file and line, and propose exact deletions or rewrites.
3. On OK, apply them. Add a changelog line saying "forgot <label>" and add the label (not the content) to "Forgotten topics" in `PROTOCOL.md`. Recording and `recall` never re-store it.

The ledger is unchanged.

### recall <question>
1. **Search** following the `CLAUDE.md` block's reading playbook (§2): index, L1, session logs (grep, then read windows), then raw chats via `--grep`.
2. **Answer** with short quotes and citations (`memory/<file>:<line>` or `(<id8> L<line>)`), with confidence and anything unverified flagged.
3. **Fix** wrong or missing memory if this chat is recording, unless the topic is on the Forgotten topics list.

### audit
Run the audit in `PROTOCOL.md` plus `build.md` Step 8 (cold-start test only if asked). Report findings, propose fixes, and apply them on OK.

### config [key=value …]
- `recording=auto|manual`: updates the index line.
- `commit=no|yes`: `.gitignore` handling, with a warning on yes.
- `timezone=<IANA>`
- `exclude-default=<list>`
- `logs=on|off`: the live telemetry (the hook's panel and Claude's `⟦CORTEX⟧` lines); updates a `Logs:` marker in the index.
- `hooks=install|remove`: shows the settings change and asks first.

With no arguments, show the current values. Mention that `cleanupPeriodDays` in `~/.claude/settings.json` controls how long Claude Code keeps transcripts, which limits how far back `/cortex all` can reach.
