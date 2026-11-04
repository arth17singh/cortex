# CORTEX v7 plan: enforced rules + a temporal knowledge base (draft for review)

Builds on `cortex-v6-plan-final.md` (same folder): eval harness first, `cortex_search`, per-message injection, PostToolUse lint, ownership split, slim rules, correctness checks. RAG/embeddings dropped by the user. New goals from the user:
1. Make mapping and intelligence genuinely smart (the review graded intelligence C).
2. Beat existing memory systems (claude-mem, Claude Code auto-memory, episodic-memory, Serena, Mem0, Zep/Graphiti, Copilot Memory, Cline Memory Bank) on intelligence, smart retrieval and historical coverage, measured, not claimed.
3. Turn prose rules into rules that are actually followed: deterministic enforcement plus LLM judgment.

## A. How prose rules become enforced rules (Claude Code mechanisms, verified in docs)
| Mechanism | Power | Use in CORTEX |
|---|---|---|
| `PreToolUse` command hook | deny a tool call, reason goes to Claude | block writes to script-owned files; block malformed memory writes; inject relevant memory before Claude edits a code file (if PreToolUse additionalContext is supported; else UserPromptSubmit) |
| `PostToolUse` command hook | feedback/block after a tool runs, same turn (`continueOnBlock`) | validate each memory write; auto-fix mechanical format; report conflicts |
| `Stop` command or prompt hook | `decision: block` + reason: Claude must continue (8-continuation cap, `stop_hook_active`) | the **capture gate**: if this turn produced a decision, rejection, correction or durable fact that isn't recorded, Claude can't end the turn until it is |
| `UserPromptSubmit` command hook | inject context before Claude answers | per-message retrieval: entity-linked records + rejected-option guard |
| `type: "prompt"` hook | small model returns `ok`/`reason` | semantic judgments code can't make: "was a decision made this turn?", "does this reply re-propose a rejected option?" |
| `type: "agent"` hook | LLM with tools | heavier verification, e.g. checking a claimed fact against the repo |
| CLI as API (`cortex_write.py`) | schema-validated writes | Claude records typed items through a command with required fields; the script writes all structure, tags, ids, dates |

Rule-by-rule conversion (each current prose rule → its enforcement):
- "Write in the same turn" → Stop capture gate (deterministic pre-filter: substantive turn and no `cortex_write` call; then LLM judge) blocks until recorded.
- Source tags, line ranges, ledger, map upkeep, rejected filing, history on change → code (PostToolUse + `cortex_write`).
- "Check before acting / never re-propose rejected" → UserPromptSubmit injection + a reply check (prompt hook on Stop: "did the reply propose something listed as rejected without saying so?").
- "One fact one place", caps, consolidation → code.
- "Don't use memory while reading is off" → hooks stop injecting; PreToolUse denies reads of `memory/` while off.
- Storage test (what's worth keeping) → stays LLM judgment, but checked by the capture gate.

## B. Intelligence: a temporal knowledge base, file-based and greppable
- **Typed records** in `memory/records.jsonl` (append-only, never rewritten; the source of truth for intelligence). Types: decision, rejection, fact, preference, status, lesson, question, open-item. Fields: id, type, subjects[], statement, why, alternatives, valid_from, superseded_by / valid_to, recorded_at, source {chat id8, session-log anchor, transcript line}, verified_by {code path:line | none}, confidence.
- **Entities**: `memory/entities.md` (generated): every subject with aliases, relations (part-of, depends-on, replaces), and its records timeline. Aliases come from three places: Claude at write time (required field), recall misses, and keywords.
- **Bi-temporal reasoning** (Zep/Graphiti's core idea, here in plain files): "what is true now", "what was true on Oct 5", "how did X change" answered from valid_from/valid_to chains.
- **Conflict detection at write**: `cortex_write` finds valid records on the same subject that the new one may contradict (same subject + type, overlapping statement terms) and returns them; Claude must answer `supersedes <id>` or `coexists` — the knowledge-update class where every tested system scored ≤28% (MemoryAgentBench).
- **Rendering**: topic files keep Claude's prose sections plus script-rendered sections (Current facts, Decisions, Rejected options, History) from records; "Where we are" generated from valid status + open items; MAP.md hierarchy generated from records + logs.
- **Session logs** stay the full narrative (the evidence layer); every record anchors to one.

## C. Retrieval that is smart, not just grep
1. **Entity linking** of the question (aliases, deterministic) → candidate subjects.
2. **Typed, temporal filters**: current vs historical, decisions vs rejections, time windows.
3. **Ranked text search** (BM25) over records, logs and transcripts (via ledger, exclusions respected), date-grouped.
4. **Graph expansion**: one hop to related subjects (part-of / depends-on) when the direct hit is thin.
5. **Answer pack**: current answer, its history chain, rejected alternatives, sources, verification status, and "not in memory" when nothing passes the threshold.
6. **LLM query planning** for hard questions (`/cortex recall` and complex prompts): Claude decomposes the question into typed sub-queries; per-message injection stays deterministic and cheap (≤300 tokens).

## D. Historical coverage
- Backfill pipeline: transcripts → session logs (existing) → **record extraction** (LLM, batched, schema-validated by `cortex_write`, conflicts resolved) → entities. Ledger tracks coverage of transcript lines; a second ledger column tracks record extraction per log.
- Coverage metrics in status: % of transcript lines captured, records per log, entities with ≥1 current record, % records verified, % with a history chain.

## E. Head-to-head evaluation ("beat existing systems" only where measured)
- **Corpus**: a copy of the real project (and its transcripts) plus the synthetic 720-log project for scale.
- **Question set**, modelled on LongMemEval categories plus CORTEX-specific ones, written blind: single-session facts; multi-session synthesis; temporal ("what did we use before X?"); knowledge updates (superseded facts); abstention (never stored); rejected-option re-proposal guard; exact identifiers/numbers; paraphrase with no shared words; planted instruction.
- **Systems we can run locally**: plain CLAUDE.md + notes + grep; Claude Code auto-memory (seeded the way it would be); episodic-memory (open source, local); CORTEX v5; CORTEX v7. claude-mem only in an isolated sandbox with network blocked (open privacy report). Same model, same questions, saved transcripts and scores.
- **Metrics**: accuracy per category, abstention precision, tokens loaded per chat, tokens read per answer, latency, compliance (records per substantive turn).

## F. Order
1. Eval harness + baselines recorded (v5 and the alternatives).
2. `cortex_write` + records + entities + rendering (Claude-owned vs script-owned files).
3. Enforcement hooks: PostToolUse validator, Stop capture gate (command pre-filter + LLM judge), UserPromptSubmit injection, PreToolUse protections.
4. Retrieval engine (C) + answer packs + recall line from its counts.
5. Backfill extraction for existing projects + migration via `/cortex upgrade` (after Nov 3 for the hackathon).
6. Slim rules (~1k tokens) — mostly "use cortex_write / cortex_search; here's the storage test".
7. Head-to-head evaluation, publish results in README honestly (wins and losses).

## Open questions for review
- Is the Stop capture gate (LLM judge every substantive turn) worth its latency/cost, and how to keep it from nagging?
- `cortex_write` as the only way to record facts: too rigid for Claude, or the right constraint?
- Is records.jsonl + rendered markdown the right split, or should records live in markdown front-matter?
- Can the head-to-head be made fair and cheap enough to actually run?
