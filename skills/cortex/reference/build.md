# CORTEX build and backfill procedure (v5)

`/cortex start` uses it with **scope = none**. `/cortex all` uses it with **scope = all**, plus any `only`/`since`/`last`/`exclude`/`include-skipped` options. `/cortex upgrade` runs only Step 0's upgrade and Steps 6–8.

**Variables:** `${CLAUDE_SKILL_DIR}`, `${CLAUDE_SESSION_ID}` and `${CLAUDE_PROJECT_DIR}` mean the values printed at the top of `SKILL.md`; they aren't substituted inside this file. All `memory/` paths are relative to the project root. `<id8>` = the first 8 characters of a transcript id.

## Principles

1. **Storage test:** "Would a future session be better informed, decide better, or answer better for having this?"
   - It's judgment, not a checklist.
   - Subtle details go to session logs; L1 stays lean.
   - Drop only noise, including narrative about building the memory itself.
2. **Accuracy:**
   - Verify against code or docs before stating something as fact, and tag it `(code: path:line)`.
   - Tag chat-sourced facts `(<id8> L<line>)` and label the rest "Reported, not yet verified".
   - Use read-only checks only: never start, reset or POST to servers, deploy or migrate just to verify.
3. **Conflicts:**
   - About what the system *does*, the code wins. About intent, decisions and preferences, the user's latest explicit statement wins.
   - Newer beats older. Compaction summaries are low trust.
   - Record any mismatch between code and intent as an open issue.
4. **Privacy:** never store secrets, keys, tokens, passwords, or anyone's email or phone number (`[redacted]`). Never open `.env*`, key files or credential stores.
5. **One fact, one place** among L1 files (`PROTOCOL.md` "What lives where"). Session logs and the changelog are history.
6. **The ledger is the only coverage record.** Mark only lines that were actually logged. Never read `excluded`, `skipped` or `paused` ranges unless the user includes them.
7. **Token-efficient:**
   - Make focused edits.
   - Copy templates with `cp` rather than reading them.
   - Measure transcripts with `| wc -c` (characters ÷ 4 ≈ tokens) before reading them.

## Step 0: Detect the state
- **`memory/INDEX.md` exists:** this is an **update**.
  - Read the index and `LEDGER.md`, then merge. Never overwrite good content.
  - **Upgrading from v4 (or older) to v5.** Detect by content, not the version marker: the project is pre-v5 if `memory/RULES.md` is missing or the `CLAUDE.md` block doesn't import it.
    1. **Refuse while another chat is live:** if the scanner flags any other chat `active`, stop and ask the user to close or pause those chats first; they still follow the old rules and would edit the index mid-upgrade.
    2. **Back up** `CLAUDE.md`, `memory/INDEX.md`, `memory/team/user-preferences.md` and `memory/PROTOCOL.md` to `memory/.backups/<YYYY-MM-DD-HHMM>-pre-v5/`.
    3. **Copy the rules:** `cp ${CLAUDE_SKILL_DIR}/reference/rules.md memory/RULES.md`.
    4. **Rewrite the index** to the v5 template (`PROTOCOL.md` after step 6): add `TZ:` to line 2 (from the old block or `PROTOCOL.md`); date each "Where we are" bullet with the `Last updated:` date of the L1 file it links to (today only if it links none), so bullets don't all age out on the same day; turn the L1 table into map lines that keep every noun from the old "Covers" and "Load when" columns; turn the L2 table into session-log lines that keep its "Covers" text and add the decisions and rejected options from each log's headings. Move rows beyond the newest ~10 to `sessions/README.md`. Nothing from the old tables may be lost: grep 10 distinctive nouns from the old index in the new one.
    5. **Carry over project lines:** diff the old block against `reference/claude-block-v4.md` (older blocks may lack its §5 Telemetry); any line that isn't template text (e.g. the topic-routing line) is project-specific. Routing goes into the map; anything else moves to the project's own section of `CLAUDE.md`, outside the markers.
    6. **Rewrite `PROTOCOL.md` and `_templates/`** from the v5 template (`reference/protocol-template.md`, sections 1–3), keeping `PROTOCOL.md`'s config values (commit setting, timezone, exclusions, forgotten topics).
    7. **Swap the block last:** replace the old block with the v5 stub (`reference/claude-block.md`). Leave `AGENTS.md` and other tools' files alone, and tell the user they still hold the old inline rules.
    8. **Verify:** run `/cortex status`; it must show the rules as current and the memory budget. Then tell the user to start a new chat, since this one still has the old rules in context.
  - **Upgrading from v3 or older:** first apply these, then the v5 upgrade above:
    1. Rename session logs from `_sN-` to `_<id8>-`, using the ledger's chat-to-log mapping.
    2. Create `_templates/`.
    3. Move the "Recording" config to the index line only.
  - **If `LEDGER.md` is missing:** create it from the session-log `Transcript:` headers as `mined`, but only where a header names a single non-overlapping range. List anything ambiguous for the user as `untracked`.
- **`memory/` exists but isn't CORTEX's:** ask first, or use `.memory/` and adjust every path.
- **Otherwise:** a fresh build.

## Step 1: Inventory
- **Timezone:** `date +"%Z %z"`, cross-checked with transcript clues; ask if unclear. Record the IANA name.
- **Scan:** `python3 ${CLAUDE_SKILL_DIR}/scripts/ledger_scan.py "${CLAUDE_PROJECT_DIR}" --current ${CLAUDE_SESSION_ID} --tz <IANA_TZ>`, plus `--preview` only for scope `all` (scope `none` never reads other chats). Read and act on its warnings.
- **This chat** (`${CLAUDE_SESSION_ID}`) is never mined as history. It's tracked live from the moment the command runs, or from line 1 with `--from-chat-start`.
- **Project docs and artifacts:**
  - README, design docs, specs, the existing `CLAUDE.md`;
  - untracked or git-ignored folders (`git status --ignored`), noting which won't survive a clone;
  - in large repos, read top-level docs and skim only the headings of the rest.
- **Auto-memory** at `~/.claude/projects/<slug>/memory/`, and the **code layout** (top-level tree only).

## Step 2: Scaffold
- **Topic folders:** create only folders that will have content. Typical ones:
  - `context/`: brief, goals, research;
  - `product/`: concept, demo, explanations;
  - `engineering/`: architecture, running, gotchas, gaps.
- **Write from the templates** (`reference/protocol-template.md`, `reference/ledger-template.md`):
  - `memory/PROTOCOL.md`, `memory/_templates/session.md`, `memory/_templates/l1.md`, `memory/LEDGER.md`;
  - `memory/team/user-preferences.md`: one line per preference; no project facts, no quotes (those go to the session log);
  - `memory/log/changelog.md`.
- **This chat's session log:** create it now with `cp memory/_templates/session.md memory/sessions/<YYYY-MM-DD>_<id8>-<topic>.md`, add its ledger row, and announce "Session log: `<path>`".
  - With no existing row: `skipped 1-<now-1>; live <now>-<now>`.
  - With `--from-chat-start`: capture lines 1..now-1 first and write `live 1-<now>`.
  - If a row exists: keep its ranges and only open `live <now>-<now>`.

## Step 3: Mine past chats (`/cortex all` only)
1. **Candidates:** each chat's `backfill` ranges from the scanner, never `gaps` (gaps include this chat and other open chats), filtered by the options and the default exclusions.
   - `since` and `exclude <date>` match a chat's first local date; `last N` means the N most recently active chats.
   - Chats flagged `active` are deferred ("open in another chat").
2. **Exclusions by description:** use only the `--preview` first message; never read further into a chat that might be excluded.
3. **Plan:** `SKILL.md` has already shown the plan and got an OK. Don't ask again.
4. **Measure:** `extract_transcript.py <file> <IANA_TZ> <a> <b> | wc -c` per range.
5. **Mine:** with more than about 150k tokens in total, use parallel subagents (at most 5 at once, brief below). Group tiny chats; split big ones at compaction-summary lines, or failing that near the midpoint, with a 10-line context note. Otherwise mine them yourself.
6. **Per chat, in order:**
   - If a log for that chat already covers the range, only update the ledger.
   - Otherwise write its log. A chat that already has a log gets a new part, `-pN`.
   - Integrate that chat's L1 corrections (Steps 4–5 for it), then set its ledger row `mined a-b`. An interrupted run then never loses L1 updates or double-mines.
7. **Excluded chats:** `excluded` with `none` ranges, no log.

## Step 4: Write or merge the L1 files
Use `_templates/l1.md`, source tags, and "What lives where".

## Step 5: Integrate subagent corrections critically
Verify each claim (in code, or with the extractor on the cited lines) before applying it. Fix dates and paraphrased quotes.

## Step 6: Write `memory/INDEX.md`
Follow the index template in `PROTOCOL.md`: line 2 with Recording and TZ; "Where we are" ≤8 dated one-line bullets with no commands or numbers; the topic-file map with every file's distinctive nouns and triggers; the session-log map with the newest ~10 logs, each naming its topics, decisions and rejected options. The map is how Claude finds old and subtle information, so favour complete nouns over brevity, within the memory budget.

## Step 7: Install `CLAUDE.md`, hooks, git setting, auto-memory
1. **Rules and `CLAUDE.md` block:** `cp ${CLAUDE_SKILL_DIR}/reference/rules.md memory/RULES.md`, then insert the stub from `reference/claude-block.md` into the project's `CLAUDE.md` with `{{SKILL_DIR}}` set to the resolved `${CLAUDE_SKILL_DIR}` (replace an older block between the CORTEX markers), keeping other content.
2. **Recording mode:** ask once if unset: `auto` (recommended) or `manual`.
3. **Hooks:** check `~/.claude/settings.json` and `.claude/settings.json` for a command containing `cortex_hook.py`. If it's missing, show the user this snippet and, with their OK, merge it into the file they choose:
   - back up first;
   - parse the JSON;
   - append to the existing `hooks` arrays without removing entries;
   - write it back and re-parse to validate.

   ```json
   {"hooks": {
     "SessionStart": [{"hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/cortex/scripts/cortex_hook.py\"", "timeout": 20}]}],
     "Stop": [{"hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/skills/cortex/scripts/cortex_hook.py\"", "timeout": 10}]}]
   }}
   ```
   The hooks are silent in projects without `memory/LEDGER.md`.
4. **Commit `memory/`?** Default no: add `memory/` to `.gitignore` and check with `git check-ignore memory/INDEX.md`. If it was already tracked, suggest `git rm -r --cached memory/` (don't run it without consent). If yes, warn that teammates will see quotes, and that each machine's transcripts differ.
5. **Auto-memory:** show the plan and wait for an OK. Move project-specific facts into `memory/` and the migrated files to `memory/.migrated-automemory/`. Leave cross-project facts. Reduce `MEMORY.md` to `- Project context lives in <abs path>/memory/INDEX.md; follow CLAUDE.md.`

## Step 8: Self-check (fix every failure)
- [ ] The index and the files on disk match both ways; caps hold (`PROTOCOL.md`).
- [ ] Memory caps hold (`PROTOCOL.md` "Caps"), and `/cortex status` shows no consolidation reason. `memory/RULES.md` is byte-identical to `reference/rules.md` (`cmp`).
- [ ] `grep -n '{{' CLAUDE.md memory/PROTOCOL.md memory/INDEX.md` returns nothing; the three `@memory/...` imports each sit on their own line, outside code spans.
- [ ] No fact appears in two L1 files: grep 5 key numbers and paths.
- [ ] `ledger_scan.py --current ${CLAUDE_SESSION_ID}` shows no `backfill` except what the user chose not to mine, and no warnings.
- [ ] Hooks installed or declined; auto-memory is only the pointer.
- [ ] No secrets or contact data. Review every hit:
  `grep -rnIE 'AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_|xox[abpr]-|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|[a-z]+://[^/ :@]+:[^@ ]+@|(api[_-]?key|secret|passw(or)?d|bearer|access[_-]?key)["'\'' ]*[:=]' memory/ CLAUDE.md`
  and `grep -rnIE '[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}' memory/ CLAUDE.md`.
- [ ] **Cold-start test** (fresh builds and `/cortex all`): a fresh subagent given only `CLAUDE.md`, `INDEX.md` and the preferences answers three questions: what the project is and where it stands, how to run or use it, and why <a real decision> was made and where to look. Fix the gaps it finds.

## Step 9: Report
Cover:
- what was created or updated;
- the chats covered, excluded and skipped;
- the recording mode, hooks and commit setting;
- the measured rules size and memory budget use (characters ÷ 4);
- anything important discovered;
- the self-check results;
- that it's safe to clear the chat.

## Subagent brief (one per chat or range; fill in the `{{…}}` values)
> Write durable memory from part of one Claude Code transcript, so a future model with no access to it understands what was discussed, answered (the substance), decided and why, and produced.
> - **Read first:** `memory/INDEX.md`, then only the 1–3 L1 files whose "Load when" matches this chat's topics. The template is `memory/_templates/session.md`; don't read anything else.
> - **Source:** `{{JSONL_PATH}}`, lines `{{A}}`–`{{B}}`. Chat `{{ID8}}`. Skip ranges: `{{SKIP or none}}`. Context note: `{{NOTE or none}}`.
> - **Read with** `python3 {{SKILL_DIR}}/scripts/extract_transcript.py {{JSONL_PATH}} {{IANA_TZ}} {{A}} {{B}}`, paging in chunks. Use a unique scratch subfolder.
> - **Write only** `memory/sessions/{{FILENAME}}` (Exchanges last, each heading ending `(L<a>-<b>)`).
> - **What to keep:** apply the storage test, keep subtle details, and quote the user's key sentences verbatim. Drop noise.
> - **Never copy** secrets, tokens, keys, passwords, or anyone's email or phone number (`[redacted]`).
> - **Final answer:**
>   - the file written, with its line count;
>   - L1 corrections and additions, each with a source tag `({{ID8}} L<line>)` and marked "verified in code/transcript" or "inferred".
