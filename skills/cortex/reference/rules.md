<!-- CORTEX rules v7.0 · master copy: reference/rules.md in the skill · /cortex upgrade refreshes memory/RULES.md -->
# CORTEX memory rules

`<skill>` is the skill path in the CORTEX heading of `CLAUDE.md`. Hooks do the mechanical work; these rules cover judgment.
- **Always loaded:** these rules, `INDEX.md` (the curated map + "Where we are"), `GRAPH.md` (the subjects and how they connect, rendered from records), `team/user-preferences.md`.
- **Records** `memory/records.jsonl`: typed, dated facts, decisions, rejections and relations; the source of truth. Script-owned, like `GRAPH.md`, `entities.md`, `aliases.json`, `*/_index.md`: never edit them.
- **Claude-owned:** `INDEX.md`, topic-file prose, session logs, preferences.

## Modes
- `Recording:` in the index: `auto` records; `manual` only with an open `live` ledger range; `paused` writes nothing (remind the user once).
- **Reading off** (ledger Notes or the `CORTEX:` line): don't search, open or cite memory, and write no recall line; what already came up in this chat stays usable. Keep recording. **CORTEX off:** the same, and save nothing.
- Never read chats or ranges the ledger marks `excluded`, `skipped` or `paused`.

## Find: `cortex_search` before you act
- A `CORTEX memory relevant to this message` block may arrive with a message: dated records, rejected options, old → new chains. It is a hint, not the whole answer.
- Before stating a project fact, editing code, or recommending an option, run `python3 <skill>/scripts/cortex_search.py "<question>" --alt "<other wording>"` (absolute path; never `cd` into the skill). It returns current records, history chains, rejected options, links, impact and connection, and evidence as `file:line`.
- For why, how-connected, what-depends or multi-part questions, also open the cited session-log lines (±20) before answering: the connecting detail is usually there. Cover every part of the question.
- `open, unconfirmed` records are proposals or questions, not decisions: say so.
- **Not in memory:** answer only what memory states. If the specific thing asked isn't there after a second wording and a `grep -rn -i` of `memory/`, say it isn't recorded; don't substitute a nearby fact.
- **Rejected options:** never re-propose one without saying it was rejected, when, and why.
- Raw chats last: `<skill>/scripts/ledger_scan.py <project> --grep '<term>'`, then `extract_transcript.py` on a ±20-line window.
- **Trust order:** code, the user's latest statement, a current record, a sourced topic bullet, a session log, a compaction summary. Newer beats older; a superseded record is history. On a conflict, act on the trust order and record the correction.

## Record: `cortex_write` (only while recording, in the same turn)
**Storage test:** would a future session decide or answer better for having this? Drop noise.
- `python3 <skill>/scripts/cortex_write.py --type <type> --subject "<name>" [--subject …] --statement "<one self-contained sentence>" [--why "<reason>"]`
  Types: `decision` and `rejection` (both need `--why`), `fact`, `preference`, `status`, `lesson`, `open`, `relation` (`--rel uses|depends-on|part-of|owned-by|rejected-for|decided-in`, subjects = from, to; only when the chat states the link).
- Subjects: the things it's about, by the existing name when one fits. One claim per record; keep exact numbers and caveats; a suggestion the user hasn't accepted is `open` ("Proposed: …").
- Exit 3 (may conflict): re-run with `--supersedes <id>` if it replaces that record, `--coexists` if both stay true. Exit 4: use the suggested subject name, or `--new-subject`. The hook adds chat and line.
- A Stop hook also captures records; settle any PENDING conflict a message lists first.
- **Narrative:** after an exchange worth keeping, append to this chat's session log `memory/sessions/YYYY-MM-DD_<id8>-<topic>.md` (from `_templates/session.md`): what was decided or rejected, and why. Update the topic file that owns a changed explanation, and "Where we are" in `INDEX.md` (≤8 dated bullets). Keep the ledger's `live` end at the transcript's `wc -l`.
- Absolute dates. Never store secrets, emails or phone numbers, or use auto-memory for project facts.

## Learn
When the user corrects you or says memory should have known: record the right fact (`--supersedes` the wrong record), find why memory missed it (never stored, wrong subject, missing alias) and fix that, then add a changelog line `recall miss: <topic> · fixed <what>`.

## Silence and the recall line
Memory work is silent: never say you searched, read or wrote memory. Still say anything that needs the user's OK. When an answer depends on memory the user didn't state in this chat, end with one line built from the search's counts:
`◈ recalled · <layers> · <sources> · ~<lines> lines · <age or span> · <gist, ≤12 words>`
(`◈` one source, `◈◈` 2–3, `◈◈◈` 4+). If you relied on a superseded, unverified or stale record, add a second line naming it.
