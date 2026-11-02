# CORTEX protocol and template files (v5)

At build time, write these three files from the sections between the `=====` markers, in the third person ("the user", never "I"):
- `memory/PROTOCOL.md` (section 1);
- `memory/_templates/session.md` (section 2);
- `memory/_templates/l1.md` (section 3).

Replace the `{{…}}` values.

===== 1. memory/PROTOCOL.md
<!-- CORTEX v5 -->
# Memory protocol: config, conventions, caps, audit

Read on demand: when creating files, restructuring memory, consolidating, or running `/cortex audit`. Day-to-day rules are in `RULES.md` (a copy of the skill's `reference/rules.md`; never edit it here).

## Config (set by `/cortex start`, `/cortex all` and `/cortex config`)
- Recording: shown only on the index "Recording" line (`auto`, `manual`, or `paused (was <mode>) since <date time>`).
- Commit `memory/` to git: {{no | yes}}. If no, `memory/` is in `.gitignore`.
- Timezone: {{IANA_TZ}} (also on the index's second line, where the rules read it)
- Rules: {{import | inline}} (`inline` copies `RULES.md` into the `CLAUDE.md` block, for tools that don't follow `@` imports)
- Default exclusions for `/cortex all`: {{none | list}}
- Forgotten topics (never re-store): {{none | labels}}
- Per-chat coverage, exclusions, skips and pauses: `LEDGER.md` (the only coverage record).

## Naming and identity
- **A chat is identified by the first 8 characters of its transcript id** (e.g. `e016c8fe`); the SessionStart hook shows it.
- **Session logs:** `sessions/YYYY-MM-DD_<id8>-<short-topic>.md`. Extra parts use `-p2`, `-p3`. The date is the local date the part starts.
- **L1 files:** `<topic>/<kebab-case>.md`.
- **Source tags** on L1 bullets: `(<id8> L<line>)`, `(<id8>)` for a whole chat, or `(code: path:line)` when verified in code. Untagged bullets are treated as unverified.
- **Transcript line numbers** are 1-based, as in `wc -l`.

## What usually passes the storage test (examples, not a whitelist)
- Decisions and their reasons; alternatives rejected and why
- User requirements, preferences, corrections, rejections (their words go in the session log)
- Findings, research results, insights, surprising behaviour
- Substance of explanations likely to be asked again
- Nuances, caveats, numbers, calibrations, timings
- Ideas floated but not pursued; open questions; risks
- Bugs with cause and fix; lessons about tools and process
- Status, next steps, artifact paths, sources and links

**Noise to drop:** chit-chat, retries, polling, duplicates, content already in repo docs or code, and narrative about building the memory system itself (one changelog line is enough).

## What lives where (one fact, one place)

| Content | Lives only in | Elsewhere |
|---|---|---|
| Numbers, names, paths, commands, ports | one owning L1 file | a link to it |
| Status, open issues, next steps | index "Where we are" (≤8 dated one-line bullets) | the detail stays in L1 |
| Routing: what each file holds, which log covers what | the index map, `sessions/README.md`, folder `_index.md` files | nothing else |
| Rejected alternatives | session log (why, in full) + a `Rejected:` bullet in the owning L1 file | — |
| Procedure | `RULES.md` (from the skill) | never restated |
| Templates, caps, audit, config | this file and `_templates/` | linked |
| Coverage per chat | `LEDGER.md` | nothing else states line numbers as truth |
| How the user works | `team/user-preferences.md` (one line each) | quotes go to session logs |
| Why, history, exact wording | session logs | L1 cites them with source tags |

## Caps and rollovers
- L1 files under ~150 lines. Split oversized ones into a subfolder, update the index, and leave a one-line pointer.
- Session-log parts under ~300 lines; start `-pN+1` past that.
- `team/user-preferences.md` under ~40 lines.
- **Memory L0 is bounded by these caps:** ≤8 "Where we are" bullets, ≤10 session logs in the map, ≤6 files listed per folder, ≤40 preference lines. Filled to every cap it measures about 3,000 tokens (≈ 12,000 characters), which is the ceiling `/cortex status` checks as a backstop. The rules are a fixed cost, budgeted separately.
- The index map lists the ~10 newest session logs; older lines move, unchanged, to `sessions/README.md`, which the index links to.
- A topic folder with more than ~6 files gets `<folder>/_index.md` (same line format); the index then keeps one line for the folder.
- Changelog over ~150 lines: move all but the newest ~60 entries to `log/changelog-archive-YYYY.md`.

## Index template
# Project memory: index
Last updated: YYYY-MM-DD · Recording: <auto | manual | paused (was …) since …> · TZ: <IANA name>

## Where we are
- <≤8 one-line bullets, each dated (YYYY-MM-DD) and linking its owning L1 file; mark open or pending items "open:"; no commands, ports or numbers>

## Map: topic files (L1)
<one line per folder. Per file: its name, then the nouns it holds, then "for" and the situations that should load it. Keep every distinctive noun: this is how Claude notices that memory covers a topic.>
- `<folder>/` <file>: <noun>, <noun>, <noun>; for <trigger>, <trigger> · <file>: …
- `<big-folder>/` <one-line scope> → `<big-folder>/_index.md`

## Map: session logs (L2, newest ~10; older in `sessions/README.md`)
- `<YYYY-MM-DD>_<id8>-<topic>.md`: <topics; decisions; rejected options, as nouns>

Other sources: <repo docs, artifacts>. Rules `RULES.md` · coverage `LEDGER.md` · config, caps, consolidation `PROTOCOL.md` · templates `_templates/`.

## Consolidation (when a cap above is exceeded, a "Where we are" bullet is older than 14 days, or memory L0 passes its ~3,000-token ceiling; the hook and `/cortex status` list the reasons)
Moves detail one level down. Guarantees:
1. **Back up first:** copy `INDEX.md` and `team/user-preferences.md` to `memory/.backups/<YYYY-MM-DD-HHMM>/`.
2. **Never delete, only move:** copy the text to its target, `grep` that it is there, then remove it from L0, all in the same turn. Every move leaves a pointer or a map entry.
3. **What moves, in order:**
   - session-log lines beyond the newest ~10 → `sessions/README.md`;
   - a folder's file entries, once the folder has more than ~6 files → `<folder>/_index.md`;
   - "Where we are" bullets older than 14 days → the body of their owning L1 file (never its `Summary:` line);
   - preferences that apply to one area only → that area's L1 file, with a one-line pointer left in the preferences.
4. **What never moves:** bullets marked "open:", pending decisions and next steps (they move to the owning file's open-threads section only once resolved); "never" and "always" preferences; the map's nouns.
5. **Re-verify on the way:** a fast-changing fact being moved (status, "untested", "no commits") is checked against the code, or marked "not yet verified".
6. **Log it:** one changelog line per move (`moved <what> from <L0 section> to <file>`), then report the before/after size.

## Hygiene
- Merge files that overlap.
- "Save" or "remember" requests go to the owning file.
- If teammates edit `memory/` through git, pull first and keep edits small.
- Back up git-ignored artifacts that memory points to into a git-ignored backup folder; never back up `.env*`, key or credential files.

## Memory audit (`/cortex audit`, or about every 10 sessions)
1. The index and the files on disk match both ways; caps hold.
2. No fact is stated in two L1 files (grep the key numbers and paths).
3. The ~5 L1 files with the oldest `Last updated:` are re-verified against the code; tags are refreshed.
4. `ledger_scan.py` shows no unexpected `backfill` and no warnings.
5. Every `excluded` chat has no session log and no bullets tagged with its id.
6. Auto-memory holds only the one-line pointer, and hooks are installed (`/cortex status`).
7. `RULES.md` is identical to the skill's `reference/rules.md` (`/cortex status` checks it); if not, `/cortex upgrade`.
8. Routing quality: every L1 file has its distinctive nouns in the map; new L1 bullets carry source tags and new session-log headings carry `(L<a>-<b>)` (status counts the gaps). Fix forward; don't rewrite history.

===== 2. memory/_templates/session.md
# Chat <id8>: <topic>

Summary: <two lines>
Date (local): YYYY-MM-DD
Transcript: <transcript path>
Related: <L1 files touched>

## Decisions and rationale        (refreshed at checkpoints)
## Alternatives rejected (why)     (every option turned down, with the reason)
## Problems and fixes
## Artifacts
## Open threads / next steps
## Exchanges                      (append-only; always last; each heading ends with (L<a>-<b>))
### <local HH:MM> <short title> (L<a>-<b>)
- **Asked:** "<short verbatim quote>"
- **Answer / work:** <substance>
- **Outcome:** <artifacts, decisions with why, follow-ups>

===== 3. memory/_templates/l1.md
# <Topic title>

Summary: <one or two lines: what this file answers>
Last updated: YYYY-MM-DD. Related: <memory files>.

## <Section>
- <fact | decision (why) | rule | explanation> <source tag>

## Rejected alternatives
- Rejected: <option> (<why>) <source tag>

## Reported, not yet verified
=====
