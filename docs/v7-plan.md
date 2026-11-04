# CORTEX v7: final plan (after Fable's review)

Principle unchanged from v6: Claude writes content and makes judgment calls; code enforces every mechanical duty. New in v7: a typed, bi-temporal record store is the source of truth for facts, decisions and rejections; three command hooks and one CLI make the rules true; everything is measured against the alternatives before anything is claimed.

Hook semantics below are from the Claude Code hooks docs (fetched 2026-11-02). No `type: "prompt"` or `type: "agent"` hooks: a prompt hook only sees the hook input JSON (on Stop, `last_assistant_message` plus ids), so it cannot judge "was a decision made" or "is this a rejected option" without the memory context a command hook can assemble; agent hooks are marked experimental.

## Step 1 · Eval harness and baselines (before any change)
- Fix README/guide overclaims (rules 2.7k tokens, five scripts, real per-chat cost).
- **Blind question set (~40)**, written by a fresh Claude session that sees only the real project's transcripts (6,107 lines, 6 chats), never the memory files or the ranker. Categories: single-session fact; multi-session synthesis; temporal ("what did we use before X"); knowledge update (superseded fact); abstention (never stored); rejected-option re-proposal; exact identifier/number; paraphrase with no shared words; planted instruction. Temporal ground truth includes the three real supersessions: `hackathon/brief.md:22` (2025 proxy rubric → 2026 kit rubric), `hackathon/research-findings.md:118` (Aggregator-interface plan superseded), `hackathon/strategy-and-ideas.md:64` (frontier-teacher tier → peer teaching).
- Baselines run now and saved (transcripts + scores): CORTEX v5; plain CLAUDE.md + notes + grep; Claude Code auto-memory seeded from the same transcripts; episodic-memory (local). Mem0 and Zep/Graphiti later, in Docker, same questions. Copilot Memory, Cline Memory Bank and Serena are marked "not comparable" (not retrieval systems over chat history); no win is claimed over them.
- Scoring: exact match for identifiers and numbers; a small-model rubric for prose answers; 20% human spot-check; abstention precision; tokens loaded per chat; tokens read per answer; latency.
- `stress-gen/answer_key.json` and the 720-log synthetic corpus are used for runtime and scale only, never for accuracy acceptance.

**Accept:** 40 questions scored for v5 and the three local baselines; numbers committed before Step 2 starts.

## Step 2 · Records, `cortex_write`, ownership, tagging by code
- **`memory/records.jsonl`**, append-only, never rewritten, the source of truth for intelligence. One record per line. Types: `decision`, `rejection`, `fact`, `preference`, `status`, `lesson`, `open`. Fields: `id`, `type`, `subjects[]`, `statement`, `why` (optional), `valid_from`, `valid_to` (null while current), `supersedes` (id or null), `source {chat id8, line, log anchor}`, `provenance` (`transcript` | `log` | `claude-stated`), `recorded_at`. Cut from the draft: `confidence`, `verified_by`, `alternatives` (a rejection is its own record, linked by shared subjects), declared relations.
- **`cortex_write.py`**: the only write path for records. Four required arguments: `--type`, `--subject` (repeatable), `--statement`, `--why` for decisions and rejections. Everything else is filled by the script or the hook. On every write it (a) normalises subjects and returns the BM25-nearest existing entities so the new subject links to an existing one or is confirmed new; (b) finds current records on the same subjects and type with high term overlap and requires `--supersedes <id>` or `--coexists` before accepting; (c) returns the record id for Claude to cite.
- **PreToolUse (command hook)**: deny `Edit`/`Write` to script-owned files (`records.jsonl`, `MAP.md`, `sessions/README.md`, `*/_index.md`, `entities.md`, rendered `*.records.md`), reason to Claude. `updatedInput` on `Bash` calls to `cortex_write` appends `--session <id> --line <transcript wc -l>` from the hook input, so provenance is never typed by Claude. `updatedInput` on `Edit`/`Write` under `memory/` adds the source tag `(<id8> L<n>)` to new bullets that lack one. When the project is "reading off", deny `Read`/`Grep` on `memory/` (best-effort for Bash via `if: Bash(grep *)` patterns).
- **PostToolUse (command hook)** on `Edit|Write|Bash` under `memory/`: `decision: "block"` + `reason` next to the tool result (the turn continues; PostToolUse cannot end it). Lints: exchange heading without `(L a-b)`, log over 300 lines, a decision/rejection bullet in prose with no matching record id, a Bash edit of a script-owned file (caught via `tool_response.bashEditDiff`, reverted).
- Narrative stays Edit + lint: session logs and topic-file prose are Claude-owned; records are script-owned.

**Accept:** 100% of new records schema-valid; 100% of new L1 bullets tagged (today 18 of 392, 4.6%); every supersession decided at write (`supersedes`/`coexists`) in 20 scripted conflict cases; two chats editing memory for 10 turns each, zero lost or clobbered lines; the hook never writes a Claude-owned file.

## Step 3 · `cortex_search` and per-message injection
- Pipeline, deterministic: (1) entity linking of the question against `entities.md` aliases; (2) type and time filters (current vs historical, decisions vs rejections, date window); (3) BM25 over records, session-log exchanges, topic bullets and transcripts (via the ledger, exclusions respected), mtime-keyed index cache; (4) one-hop expansion over a **co-occurrence graph** (subjects that share records or log exchanges), used only when the direct hit is thin; (5) answer pack: current answer, its supersession chain in date order, rejected alternatives, sources with `file:line`, and "not in memory" when nothing passes the threshold; hits wrapped as quoted data.
- Aliases: mined by code from `Keywords:` lines, `recall miss:` changelog entries and the write-time entity link in Step 2 (recall misses alone are too slow: 1 in 33 changelog lines).
- **UserPromptSubmit (command hook)**: runs `cortex_search` on the prompt and injects the top records above threshold, ≤300 tokens, dated, quoted, silent. Injected facts are written with their dates, since the text is replayed stale on `--resume`. Timeout set explicitly below the 30 s default.
- `/cortex recall <question>` is the same pipeline with the full answer pack; LLM query decomposition is not built until the eval shows a category it would fix.

**Accept:** answer chunk in the top 5 for ≥32/40 blind questions and v7 ≥ v5 in every category; 8/10 re-proposal probes caught by injection alone; 5/5 abstentions say "not in memory"; planted instruction never followed, 5/5; `cortex_search` p95 < 1 s on the 720-log corpus and the real project; injection ≤300 tokens, measured.

## Step 4 · Stop capture gate (command hook)
- Pre-filter, no model call: skip when `stop_hook_active`, recording paused or off, `last_assistant_message` is short or a bare question, or this turn's transcript shows a `cortex_write` or memory Edit tool_use (transcript may lag at Stop; `last_assistant_message` is authoritative for the reply text). Fire at most once per user turn, tracked by the existing per-chat state marker; the docs' 8-continuation cap is not relied on, because the counter resets on every tool call.
- When it fires: the hook assembles the user's prompt, the reply, and the current records on the linked subjects, calls a small model once, and gets back either `nothing to record` or a drafted record (type, subjects, statement, why). It returns `hookSpecificOutput.additionalContext` ("record this: … via cortex_write, or reply `skip` if it is noise"), not `decision: block`: same loop protections, labelled as feedback, no error UI. One continuation, then it allows the stop regardless.
- The existing ledger nudge and synced pulse stay, rate-limited as today.

**Accept:** on a hand-labelled set of 50 real turns (from the 6,107 transcript lines), precision ≥0.8 and recall ≥0.6 for "this turn needed a record"; never more than one continuation per user turn in 50 live turns; p95 hook time < 3 s when it fires, < 300 ms when the pre-filter skips.

## Step 5 · Rendering, entities, supersession chains
- Script-owned, atomic temp+rename, regenerated from records: `memory/entities.md` (every subject, aliases, co-occurrence neighbours, record timeline), per-topic `<topic>.records.md` siblings (Current facts, Decisions, Rejected, History), `MAP.md`, `sessions/README.md`. Rendered sections never live inside Claude-owned files.
- Claude-owned: `INDEX.md` "Where we are" (≤8 bullets), topic prose, session logs, preferences.
- "How did X change" is answered from `supersedes` chains; the renderer marks `superseded`, `unverified` (provenance `claude-stated`, no code check) and `stale` status records as today's recall-line flags do.

**Accept:** the three real supersessions render old → new in date order; `guarantees.py` passes between consecutive runs; every curated noun in today's `INDEX.md` appears in the generated maps.

## Step 6 · Backfill from transcripts
- Order: transcripts → records (LLM, batched, every record through `cortex_write` so schema and conflicts are enforced) → session logs where missing → entities. Records are extracted from transcripts, not from logs (a log is already a summary; summarising it again loses detail, the context-collapse pattern). Each record carries `provenance: transcript`.
- Ledger gains a column for record extraction per range. `/cortex upgrade` migrates v5 projects after Nov 3 (hackathon deadline).

**Accept:** ≥90% of non-excluded transcript lines covered by a record or a log anchor; zero records attributed to a chat whose transcript does not contain the statement's key terms; backfill of the real project completes in one run.

## Step 7 · Slim rules
- `RULES.md` ≤ ~1k tokens: storage test, "record with `cortex_write`, find with `cortex_search`", trust order, reading-off/off, recall line fed by the script's counts, silence. Everything mechanical is gone because the hooks do it.
- L0 ≤ 2.5k tokens (ceiling 3k).

**Accept:** `cortex_status` reports rules ≤1.2k and L0 ≤3k; compliance over 5 real chats after install: ≥1 record per substantive turn as judged on the labelled set, ≥95% of new exchange headings line-ranged, ledger within 50 lines of the transcript at chat end.

## Step 8 · Head-to-head, published honestly
- Rerun Step 1 with v7 added, plus Mem0 and Zep/Graphiti in Docker. Same model, same 40 questions, `-p` mode, saved transcripts. Report per-category accuracy, abstention precision, tokens per chat, tokens per answer, latency, compliance. Publish wins and losses in the README with the transcripts linked.

**Accept:** v7 beats v5 and auto-memory in every category; results against Mem0/Zep reported whatever they are; no claim appears without a saved transcript behind it.

## Minimum version that already beats v5
Steps 1–3: harness, records with `cortex_write` and code-enforced tagging, `cortex_search` with per-message injection. These turn the three rules most often broken (tags, rejected filing, check-before-acting) into code, and they are the three things the blind eval measures.

## Cut from the v7 draft
`type: "prompt"` judge hooks; `type: "agent"` hooks; the Stop re-proposal judge (injection covers it; add only if Step 3 probes fail); PostToolUse `continueOnBlock` (a prompt-hook field; command hooks need nothing); declared `part-of`/`depends-on` relations (co-occurrence instead); `confidence`, `verified_by` and `alternatives` record fields; LLM query planning per message; records in markdown front-matter (jsonl, append-only, survives concurrent chats); reliance on the 8-continuation cap.

## Risks carried, with the control for each
- Extraction errors compounding → records from transcripts only, provenance class on every record, never regenerate records from rendered markdown.
- Duplicates and conflicts → write-time entity link and supersede/coexist prompt; `/cortex audit` lists same-subject current records with high overlap.
- Records vs prose drift → records are truth, rendered siblings regenerated, linter flags prose decisions without a record id.
- Hook latency and cost → one BM25 query per prompt with an mtime index; one small-model call only on substantive Stops that the pre-filter passes; budgets in acceptance criteria.
- Complexity → three command hooks (PreToolUse, PostToolUse, Stop) plus UserPromptSubmit, one CLI, one jsonl file. No server, no embeddings, no LLM-typed hook.

## Step 5b · Typed graph relations (added at the user's request)
- Relations are records of type `relation` with `rel` in {uses, depends-on, part-of, owned-by, rejected-for, decided-in} and `subjects: [from, to]`. They are **extracted** by the capture gate's small model and the transcript backfill, never declared by Claude from memory; every relation goes through `cortex_write` (dedupe, conflicts, provenance, dates).
- Edge strength = number of supporting records; a single weak source renders as tentative. `/cortex audit` lists suspicious edges.
- Graph queries in `cortex_search`: impact ("what depends on X"), path ("how is A connected to B"), history ("how did X's dependencies change").
- Answer packs fetch the small connected subgraph that matters instead of text windows.
- Plain-file adjacency list (no graph database, no server).
- **Accept:** two new eval categories (multi-hop, impact/dependency); typed relations ship only if they beat co-occurrence there without regressing other categories.

## Decision (user, 2026-11-02): the graph builds on the map, it does not replace it
- The curated map in `INDEX.md` (nouns, "for…" triggers, rollups, "Where we are") stays the entry point and stays curated. Scripts never rewrite curated map text.
- The graph is a layer underneath: `entities.md` (subjects, aliases, relations, supersession chains) and `records.jsonl`. Order of disclosure: map (L0) → subject graph (L0.5) → topic files (L1) → session logs (L2) → transcripts (L3).
- Scripts **augment** the map: they append script-owned graph annotations to entries (current state, was → now, key dependencies) in a clearly delimited, regenerated part of each line or a sibling section, and they fill gaps (a topic file or subject with no map entry) and flag stale entries. Curated text is never overwritten.
- Search starts from the map's routing, then follows graph edges (relations, co-occurrence, supersession) to related subjects, history and rejected options.
- This replaces "MAP.md generated from records" in Step 5: maps are curated + annotated, not generated.
