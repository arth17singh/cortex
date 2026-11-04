# CORTEX v6 plan: make the rules enforce themselves, make search measurably better

Repo: `~/Developer/cortex` (skill in `skills/cortex/`). Real project: `~/Documents/Invences/Hackathons/breaking_barriers_aws` (live hackathon until Nov 3; nothing migrates there before then).

## Evidence this plan responds to
- **Real use (8 days):** 18 of 468 topic-file facts carry a source tag (4%); 4 of 10 session logs have `(L<a>-<b>)` headings; 1 `Rejected:` bullet in topic files; 0 rejected-alternatives sections; the self-test has never run. INDEX.md references a `sessions/README.md` that doesn't exist; one log is 315 lines (cap 300); the project was upgraded 3 times in one night and its rules copy already differs again.
- **Cost:** about 4.7k tokens loaded per chat (rules 2.7k + memory 2.0k). Anthropic: keep CLAUDE.md under ~200 lines; "longer files consume more context and reduce adherence"; "if a rule must always hold, use a hook". An AGENTS.md study: LLM-written context files slightly reduced task success and raised cost >20%; repository overviews didn't speed navigation.
- **Search:** recall in the stress test was mostly plain grep over rich session logs; the one structural win (12→14) was a paraphrased rejection grep can't bridge ("keyword scoring only" vs "BM25-only"). Grep also drowned in noise once ("refresh" in 18 logs). Letta: a filesystem agent with grep is competitive on LoCoMo; Cursor: semantic search adds modest gains on top of grep, best combined.
- **Correctness:** literature failures are correctness failures (context collapse when LLMs rewrite memory; stored mistakes compounding). A recall quiz checks readability, not correctness. GitHub Copilot verifies each memory's code citation before use and expires memories.
- **Fable review:** keep ledger, scan, extractor, recovery, pulse, status, storage test, L1/L2 split, `Rejected:` bullets. Cut or move: recall-line spec (~700 tok), three-switch matrix detail, rollup prose, self-test until it runs, "Silent memory" wording. Riskiest: citation-shaped confidence on untagged facts; three "before other work" directives stacked at session start.
- **README overclaims:** "~1.8k tokens" (2.7k), "three scripts" (five), "without paying for them in context window".

## Principle
Claude writes **content** (what was decided, why, what was rejected, facts). **Scripts** do every mechanical duty: maps, tags, ledger, rollups, rejected-option filing, linting, search ranking, counts. The rules shrink to the judgment calls only; memory content may grow.

## Phase 0 · Honesty and live bugs (small, ships first)
1. README/guide: replace overclaims with measured numbers from a new `scripts/measure.py` (rules tokens, memory tokens, script count), and say plainly what is enforced by code vs asked of the model.
2. Fix: index template must not mention `sessions/README.md` until it exists; cap check for oversized session logs (split into `-p2`) reported by status.
3. Save stress-test artifacts and quiz results into the repo (`tests/`), so results are reproducible, not conversational.

## Phase 1 · Maintenance engine (`scripts/cortex_maint.py`), run by the hooks
Deterministic, incremental, atomic writes, file lock (`memory/.lock`) so concurrent chats can't collide; < 1 s on a 720-log project.
1. **Map generation:** `INDEX.md` map sections and `sessions/README.md` are generated from files on disk, never hand-written:
   - per-log line from each log's headings: topics, `Decisions` bullets (bold phrase), `Alternatives rejected` bullets, Q&A questions;
   - per-file map entry from each topic file's `Summary:` and a `Keywords:` header line (Claude writes Keywords once; script falls back to TF-IDF distinctive terms across topic files);
   - hierarchical rollups (15 recent / 4 week / 6 month / quarters; folder summaries > 10 files) built by the script, with distinctive-term selection (rejected options first, then TF-IDF-ranked nouns), within the size limits. Replaces the six-guarantee prose procedure.
   - "Where we are" stays Claude-written (judgment), but the script dates new bullets and moves bullets > 14 days old (non-`open:`) into their linked file, logging each move.
2. **Provenance by code:** at Stop, any new topic-file bullet without a tag gets `(<id8> L<transcript lines now>)` appended (the chat that wrote it, approximate line). Legacy untagged bullets are counted as "legacy, unsourced", never back-filled with invented tags.
3. **Rejected options filed by code:** every bullet under a log's `Alternatives rejected` is copied (deduplicated) into the `## Rejected alternatives` section of the topic file named in the log's `Related:` line (fallback `memory/decisions/rejected.md`), tagged with the chat id.
4. **Ledger synced by code from the log's own claims:** this chat's `live` end = the highest `L<b>` in this chat's session-log headings. Integrity rule preserved: only lines a log claims are marked.
5. **Lint → precise nudge:** Stop checks the turn's memory writes (new log exchange without `(L<a>-<b>)`, topic fact missing `Keywords:`, log over 300 lines, map gaps). Mechanical issues are auto-fixed; judgment issues come back as one specific `additionalContext` line ("add Keywords: to engineering/auth.md"), silently, rate-limited.
6. **SessionStart directives prioritised:** recovery first; consolidation is now a silent script run; the self-test is deferred until after the user's first request is answered. Never three "before other work" directives.

## Phase 2 · Search engine (`scripts/cortex_search.py`) — the single way to look things up
1. **Ranked retrieval over every layer:** chunks = topic-file bullets, session-log exchanges and Decisions/Rejected bullets, rollup lines, per-log lines; optional raw transcripts through `ledger_scan` (respecting exclusions). BM25 scoring (stdlib), recency boost, layer weighting, exact-phrase and identifier boosts.
2. **Paraphrase bridge without embeddings:** Claude passes the question plus 3–6 alternative phrasings and likely identifiers (`--q "keyword scoring only" --alt "BM25" --alt "lexical ranking" …`). Cheap, uses the model's strength, fixes the Q6 class of miss. Optional local embeddings later, only if installed.
3. **Output built for reasoning:** top hits with `file:line`, date, layer, source tag, and the surrounding window; groups hits about the same subject in date order and marks the newest, so supersession is visible ("decided X Aug 14 → replaced Sep 23").
4. **Exact counts for the recall line:** the script prints sources, lines and layers read; Claude copies them into `◈ recalled …`, so the numbers are measured, not estimated.
5. **Noise control:** caps output to the best ~40 lines unless asked for more; fixes the "refresh in 18 logs" drowning.

## Phase 3 · Rules slim-down (target ~1.2k tokens, down from 2.7k)
Keep only judgment: storage test; what to write where; trust order (only "verified in code > recorded > unsourced", since tags now exist by code); check-before-acting via `cortex_search`; reading off / off; one-paragraph recall line using script counts; silence. Move procedures (consolidation, upgrade, switches, self-test) to on-demand references the skill reads when a command runs. Hook messages carry state-specific instructions only when relevant.

## Phase 4 · Correctness, not just readability
1. `scripts/cortex_verify.py`: for facts tagged `(code: path:line)` check the path exists and the line still matches; for facts naming paths, commands or ports, grep the repo; for status bullets, age. Status and the recall line show `unverified`/`stale` from this, not from model judgment.
2. **Supersession convention:** a topic-file bullet may start `Replaces: <old>` (Claude) — search groups and the map render "old → new"; the script refuses to drop the old fact, it moves it to the file's history section.
3. **No LLM rewrites of whole memory files** (context-collapse finding): consolidation is scripted; Claude edits only single bullets.

## Phase 5 · Self-test that actually runs and measures the right thing
1. **Deterministic retrieval check** every 5 changed logs, run by the hook itself (no agent): for recent decisions/rejections, does `cortex_search` with the fact's own key terms return it in the top 5? Misses → map/Keywords fixes queued as a lint nudge.
2. **Optional LLM paraphrase quiz** (existing procedure) only on `/cortex selftest`, with results saved to `memory/log/selftest.md` and transcripts to `memory/log/selftest/`.

## Phase 6 · Evidence and regression gate
1. `tests/`: synthetic active-project generator (720 logs, 118 files, needles incl. paraphrase, superseded, near-duplicate, exact number, buried-in-yesterday, never-stored, injected instruction) **plus a messy "realistic" variant** with prose rejections and no headings.
2. Deterministic suite: maintenance guarantees (nothing leaves the maps), hook states (normal / reading-off / off; chat and project), Python 3.9, search eval (top-k hit rate per needle type, with and without alternative phrasings). **Search accuracy may only go up release to release.**
3. LLM quiz harness writes saved scores; A/B v5 vs v6 on both synthetic variants and on a copy of the real project.
4. Real project migration only after Nov 3, through `/cortex upgrade`, diff shown first.

## Expected outcome
- Compliance-critical duties (tags, rejected filing, map, ledger, rollups) go from model-dependent (2–40%) to code-enforced (≈100% for the mechanical part).
- Rules ~1.2k tokens; memory map may grow to ~3–7k because it is generated, dense and relevant.
- Search: ranked, multi-layer, paraphrase-bridged, measured by a regression suite.
- Self-improvement that demonstrably runs (hook-driven retrieval checks), and correctness checks against code.

## Open questions for review
- Is auto-tagging with an approximate transcript line honest enough, or should tags be chat-only `(id8)`?
- Generated map vs Claude-curated nouns: will TF-IDF + a `Keywords:` line match the curated quality that scored 14/14?
- Should `cortex_search` replace grep entirely in the rules, or sit beside it?
- Risk of the Stop hook editing memory while Claude is mid-edit in another chat (lock design).
