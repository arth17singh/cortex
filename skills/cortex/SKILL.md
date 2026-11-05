---
name: cortex
description: "CORTEX: layered, self-maintaining project memory. Subcommands: start (record from now), upgrade (move a project to the current version), all (backfill untracked past chats), status, save, pause/resume, off/on, exclude/include, forget, recall, brief (catch me up), timeline (one subject's history), open-items, decisions (decision log), verify (stale memory), audit, selftest, config, help. Use when the user runs /cortex."
argument-hint: "help | upgrade | brief [since DATE] | timeline <subject> | open-items | decisions | verify | start [--from-chat-start] | all [only <chat>] [since DATE] [last N] [exclude X] [include-skipped] [--yes] | status | save [note] | pause [--read] [--project] | resume [--read] [--project] | off [--project] | on [--project] | exclude <chat> | include <chat> | forget <topic> | recall <question> | audit | selftest | config [key=value]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ledger_scan.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/extract_transcript.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/cortex_status.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/selftest.py *)
---

# CORTEX (v5)

**Request:** `/cortex $ARGUMENTS`
- **This chat:** session `${CLAUDE_SESSION_ID}` (short id = its first 8 characters). Find its transcript with `ls ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/*/${CLAUDE_SESSION_ID}.jsonl`.
- **Project:** `${CLAUDE_PROJECT_DIR}`. All `memory/` paths are relative to it.
- **Skill files:** `${CLAUDE_SKILL_DIR}`.

Read the first word of the request as the subcommand. If it's empty or unknown, run **help**.

## Rules for every subcommand
- **The user has full control.** Before anything that reads many chats, deletes memory, or changes git, hooks or recording settings, show exactly what will happen and wait for an OK (`--yes` skips this). Small top-ups of chats that were already recording are the exception: they just run (see **all**, step 4).
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
- **Day-to-day rules** are `memory/RULES.md`, a byte-for-byte copy of `${CLAUDE_SKILL_DIR}/reference/rules.md`, imported by the stub in `CLAUDE.md` (`reference/claude-block.md`). Conventions, caps, consolidation and the audit are in `memory/PROTOCOL.md`.
- **Old projects:** if `memory/INDEX.md` exists but `memory/RULES.md` doesn't, the project is on v4. Every subcommand except help, status and config offers `/cortex upgrade` first.

## Subcommands

### help
List the subcommands with one-line descriptions and two examples. If memory exists, add a 3-line status: recording mode, `backfill` line count, and whether hooks are installed.

### upgrade
Bring this project to the current rules and layout. Show what will change and wait for an OK.
- **Pre-v5 project** (no `memory/RULES.md`): follow `${CLAUDE_SKILL_DIR}/reference/build.md` Step 0, "Upgrading from v4 (or older) to v5", then Steps 6–8.
- **v5 or v7 project → v8** (the CORTEX block in `CLAUDE.md` says `v5` or `v7`): run `python3 ${CLAUDE_SKILL_DIR}/scripts/cortex_upgrade.py <project> --dry-run` and show the user the plan (chats, lines to read, estimated model calls; excluded chats and skipped/paused ranges are never read). On OK, run it without `--dry-run`, in the background (a v5 project needs a backfill: several minutes; a v7 project only archives and indexes: seconds). It backs up `memory/` to `memory/.backups/<stamp>-pre-v7/`, backfills `memory/records.jsonl` (v5 only), archives every recorded chat into `memory/chats/` (redacted, line-addressed, git-ignored), builds the search index (`memory/.cache/`), and installs the v8 rules and `CLAUDE.md` block. Curated files are not touched. Report the counts in two lines, then make sure the memory tools are registered once (`claude mcp add --scope user cortex -- python3 ${CLAUDE_SKILL_DIR}/scripts/cortex_mcp.py`) and the hooks from `reference/hooks-v8.json` are installed; the v7/v8 hooks stay silent in projects still on v5.
- **v8 project whose `RULES.md` differs from the skill's copy:** copy the skill's `rules.md` over `memory/RULES.md` after backing it up.
- **v5 project staying on v5, whose `RULES.md` differs from the skill's v5 copy (`reference/rules-v5.md`):** show `diff memory/RULES.md ${CLAUDE_SKILL_DIR}/reference/rules-v5.md`, then on OK back up `memory/RULES.md` and `memory/PROTOCOL.md` to `memory/.backups/<YYYY-MM-DD-HHMM>-upgrade/`, copy the skill's `rules-v5.md` over `RULES.md`, and re-render `PROTOCOL.md` and `_templates/` from `reference/protocol-template.md`, keeping `PROTOCOL.md`'s config values. Memory content (index, topic files, logs) is not touched; if the new caps call for consolidation, the next chat's start-up line will say so.
- Finish by telling the user to start a new chat, since this one still has the old rules in context.

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
4. **Small top-ups just run:** if every candidate is the unlogged tail of a chat that was already recording (its row has a `live` or `mined` range), nothing is `include-skipped`, and the total is under ~50k characters, don't ask. Do it, then say in one line what was saved (e.g. "Saved lines 173–190 of 62cba7d1."). Mention anything deferred.
5. **Otherwise show the plan:** chats and ranges with dates, previews and an estimate (`wc -c` ÷ 4); what's excluded, skipped or deferred; and what's already tracked. Wait for an OK unless `--yes`. This covers chats that never recorded, `include-skipped`, and large backfills, where there is a real choice to make.
6. Follow `build.md` Steps 0–9, with Step 3 for the confirmed ranges. Integrate L1 updates and update the ledger per chat.
7. **This chat's row:** keep existing ranges and only open or extend `live` from <now>. If there's no row, write `skipped 1-<now-1>; live <now>-<now>`. If the user wants the whole chat, capture 1..now-1 first and write `live 1-<now>`.

### status
Read-only. Run:
`python3 ${CLAUDE_SKILL_DIR}/scripts/cortex_status.py "${CLAUDE_PROJECT_DIR}" --session ${CLAUDE_SESSION_ID}`

Your entire reply is its output, verbatim, in one code block. Write nothing before or after it: no preamble, no commentary, no settings recap, no suggestions. The dashboard already covers settings, warnings and the next action.

### save [note]
- **With no note:** run a full checkpoint ("Checkpoint" in `RULES.md`).
- **With a note:** store it in its owning L1 file, with a source tag, and in the session log, even if this chat is paused. Confirm where it went.

### pause [--read] [--project]
Three switches: `pause` stops **saving** (memory is still read), `pause --read` stops **reading** (saving goes on), and `off` stops both.
- **This chat (default):** set its current `live` end to <now-1> and add `paused <now>-`. Write nothing else from this chat except `/cortex save <note>`. Confirm: "Saving paused at line <now>; memory is still read. Other and future chats are unaffected."
- **`--project`:** set the index line to `Recording: paused (was <mode>) since <YYYY-MM-DD HH:MM>`, add `paused <now>-` to every row with an open live range (`<now>` = that chat's `wc -l`), then confirm. New chats in this project don't record; reading still works.
- **`--read` (this chat):** add `reading off` to this chat's ledger Notes cell (create the row if needed); recording is unchanged. From this point on, don't open, grep or cite memory, and write no recall line. What has already come up in this conversation stays usable, including things memory surfaced earlier, but don't bring in anything known only from memory (the always-loaded index, map or files read earlier) that hasn't come up in this chat. Still record as usual: open the session log, the index and the owning topic file only to write to them. Confirm: "Reading off for this chat from here; still saving. What we've already discussed stays in play. For a clean slate, `/cortex pause --read --project` and a new chat. `/cortex resume --read` turns reading back on."
- **`--read --project`:** replace the CORTEX block in `CLAUDE.md` with the reading-off stub from `${CLAUDE_SKILL_DIR}/reference/claude-block.md` (keep the skill path). New chats load only the rules and keep recording. Confirm, and say that this chat still has memory loaded (`/cortex pause --read` covers it).

### resume [--read] [--project]
- **This chat:** close the pause as `paused <a>-<now-1>` and append a new segment `live <now>-<now>`. Never extend a live range across a pause.
- **`--project`:** restore the `was <mode>` value and close open pauses at each chat's current `wc -l`.
- **`--read` (this chat):** remove `reading off` from the Notes cell. Memory is used in answers again from this point.
- **`--read --project`:** put the normal stub from `${CLAUDE_SKILL_DIR}/reference/claude-block.md` back in place of the reading-off stub (same skill path). New chats load memory again.

### off [--project]
Turn CORTEX off: no reading and no saving.
- **This chat (default):** pause saving as in `pause`, and add `cortex off` to the Notes cell. From this point on, don't open, grep or cite memory, and write no recall line. What has already come up in this conversation stays usable, including things memory surfaced earlier, but don't bring in anything known only from memory (the always-loaded index, map or files read earlier) that hasn't come up in this chat. Confirm: "CORTEX off for this chat from here: not reading, not saving. What we've already discussed stays in play. For a clean slate, `/cortex off --project` and a new chat. `/cortex on` turns it back on."
- **`--project`:** do `pause --project`, then replace the CORTEX block with the off stub from `${CLAUDE_SKILL_DIR}/reference/claude-block.md`. New chats load nothing and the hooks stay quiet apart from one start line. Confirm, and say that this chat still has memory loaded (`/cortex off` covers it).

### on [--project]
- **This chat:** resume saving as in `resume`, and remove `cortex off` from the Notes cell.
- **`--project`:** put the normal stub back in place of the off stub (same skill path), then `resume --project`. Tell the user that new chats load memory again, and that a new chat is the clean way back.

### exclude <chat>
Permanently leave a chat out of memory. The chat can be named by id prefix, date, or description.
1. **Identify it:** IDs and dates from the scanner. For a description, compare only the first-message previews. If it's ambiguous, list the candidates and ask.
2. **Mark it:** set its row to `excluded` with ranges `none`; this is the only operation allowed to shrink ranges. If it's this chat, stop recording now.
3. **If it was already in memory,** show its session logs and every L1 bullet tagged with its id (plus anything else that grep finds for distinctive terms from its logs). Offer to purge. On OK, delete them and add a changelog line without the content.
4. **v8:** its chat archive (`memory/chats/<id8>.txt`) is deleted and the index refreshed on the next archive run; run `python3 ${CLAUDE_SKILL_DIR}/scripts/cortex_archive.py --root <project> --all --index` to do it now. Records drawn from it stay until purged in step 3.

### include <chat>
- **Excluded chat:** set it to `untracked` with no ranges.
- **Skipped or paused part:** delete that range.

Then offer `/cortex all only <chat>`.

### forget <topic>
1. Search `memory/` for the topic.
2. Show every match with its file and line, and propose exact deletions or rewrites.
3. On OK, apply them. Add a changelog line saying "forgot <label>" and add the label (not the content) to "Forgotten topics" in `PROTOCOL.md`. Recording and `recall` never re-store it.
4. **v8:** `memory_search` also finds it in the chat archive. For each chat range where it appears, offer to mark that range `skipped` in the ledger; the next archive run removes those lines from `memory/chats/` and the index (`cortex_archive.py --root <project> --all --index` does it now).

The ledger is unchanged.

### recall <question>
1. **Search** with `memory_search` (or `python3 ${CLAUDE_SKILL_DIR}/scripts/cortex_search.py "<question>" --alt "<other wording>"`): records, rejected options, old → new chains and passages from the archive of every chat, each with a pointer. Give 1–3 alternative wordings.
2. **Open** the pointers the answer rests on with `memory_open` (`cortex_search.py --open "<pointer>"`) and quote the exact words.
3. **Answer** with short quotes and pointers (`chat <id8> L<line>` or `memory/<file>:<line>`), the match strength, and anything unconfirmed, replaced or stale flagged. On a weak match after a second wording, say it isn't recorded.
4. **Fix** wrong or missing memory if this chat is recording, unless the topic is on the Forgotten topics list.

### brief [since YYYY-MM-DD]
Catch the user up: run `python3 ${CLAUDE_SKILL_DIR}/scripts/cortex_tools.py brief [--since DATE]` (or `memory_brief`) and summarise what changed across every chat in this project: decisions, rejections, status changes and new open items, newest first, with pointers. Default: the last 3 days. (New chats already get a short catch-up automatically when something changed since the last session.)

### timeline <subject>
One subject's whole history: `cortex_tools.py timeline "<subject>"` (or `memory_timeline`). Present it old → new: what was decided, what replaced what and why, what was rejected, with dates and pointers. Good for "how did X evolve", "what did we use before".

### open-items
Unresolved questions and proposals awaiting a decision, oldest first: `cortex_tools.py open-items [--all]`. Offer to settle the ones the user can answer now: record the decision with `memory_record` and `supersedes=<the open item's id>`.

### decisions
The decision log: `cortex_tools.py decisions --write` renders `memory/DECISIONS.md` (every decision and rejection with its reason, date and pointer, replaced ones struck through), a file teammates can read or review in a pull request. Show the path and the counts.

### verify
Stale-memory check: `cortex_tools.py verify` lists current records that name code files which changed or disappeared since they were recorded. For each, check the code, and record the correction with `supersedes=<id>` where memory is wrong.

### audit
Run the audit in `PROTOCOL.md` plus `build.md` Step 8 (cold-start test only if asked). Report findings, propose fixes, and apply them on OK.

### selftest
Run the self-test now, regardless of when the last one ran: follow `${CLAUDE_SKILL_DIR}/reference/selftest.md` with `selftest.py --all`. It also runs on its own: the SessionStart hook asks for one after 5 changed session logs, at most once a day.

### config [key=value …]
- `recording=auto|manual`: updates the index line.
- `commit=no|yes`: `.gitignore` handling, with a warning on yes.
- `timezone=<IANA>`
- `exclude-default=<list>`
- `logs=on|off`: the hooks' live lines (the status line at start-up and the `⟲ CORTEX synced` line after a turn that changed memory); updates a `Logs:` marker in the index. Claude never reports memory writes in chat either way.
- `rules=import|inline`: `inline` copies `RULES.md` into the `CLAUDE.md` block (for tools that don't follow `@` imports); `import` restores the stub.
- `selftest=on|off`: the automatic self-test; updates a `Selftest:` marker in the index (`/cortex selftest` still works when off).
- `hooks=install|remove`: shows the settings change and asks first.

With no arguments, show the current values. Mention that `cleanupPeriodDays` in `~/.claude/settings.json` controls how long Claude Code keeps transcripts, which limits how far back `/cortex all` can reach.
