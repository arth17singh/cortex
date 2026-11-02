# CORTEX protocol and template files (v4)

At build time, write these three files from the sections between the `=====` markers, in the third person ("the user", never "I"):
- `memory/PROTOCOL.md` (section 1);
- `memory/_templates/session.md` (section 2);
- `memory/_templates/l1.md` (section 3).

Replace the `{{…}}` values.

===== 1. memory/PROTOCOL.md
<!-- CORTEX v4 -->
# Memory protocol: config, conventions, caps, audit

Read on demand: when creating files, restructuring memory, or running `/cortex audit`. Day-to-day rules are in the `CLAUDE.md` block.

## Config (set by `/cortex start`, `/cortex all` and `/cortex config`)
- Recording: shown only on the index "Recording" line (`auto`, `manual`, or `paused (was <mode>) since <date time>`).
- Commit `memory/` to git: {{no | yes}}. If no, `memory/` is in `.gitignore`.
- Timezone: {{IANA_TZ}}
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
| Status, open issues, next steps | index "Where we are" (≤8 one-line bullets) | the detail stays in L1 |
| Procedure | the `CLAUDE.md` block | never restated |
| Templates, caps, audit, config | this file and `_templates/` | linked |
| Coverage per chat | `LEDGER.md` | nothing else states line numbers as truth |
| How the user works | `team/user-preferences.md` (one line each) | quotes go to session logs |
| Why, history, exact wording | session logs | L1 cites them with source tags |

## Caps and rollovers
- L1 files under ~150 lines. Split oversized ones into a subfolder, update the index, and leave a one-line pointer.
- Session-log parts under ~300 lines; start `-pN+1` past that.
- `team/user-preferences.md` under ~40 lines.
- Index under ~2,500 characters of tables and status, listing only the ~10 newest session logs. Older rows move to `sessions/README.md`, which the index links to.
- Changelog over ~150 lines: move all but the newest ~60 entries to `log/changelog-archive-YYYY.md`.

## Index template
# Project memory: index
Last updated: YYYY-MM-DD · Recording: <auto | manual | paused (was …) since …>

## Where we are
- <≤8 one-line bullets with absolute dates and links to the owning L1 file; no commands, ports or numbers>

## L1: topic files
| File | Covers (nouns) | Load when |

## L2: session logs (newest ~10)
| File | Date | Covers |

Other sources: <repo docs, artifacts>. Coverage: `LEDGER.md`. Conventions: `PROTOCOL.md`.

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

===== 2. memory/_templates/session.md
# Chat <id8>: <topic>

Summary: <two lines>
Date (local): YYYY-MM-DD
Transcript: <transcript path>
Related: <L1 files touched>

## Decisions and rationale        (refreshed at checkpoints)
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

## Reported, not yet verified
=====
