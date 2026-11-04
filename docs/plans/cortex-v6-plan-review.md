# Review of cortex-v6-plan.md

## 1. Will it raise compliance and search accuracy?

**Will:**
- Phase 1.2–1.4 (tags, rejected filing, ledger sync by code). The raw material exists: 5 of 10 real logs have an `## Alternatives rejected (why)` section and 4 of 10 have `### … (L a-b)` headings (17 of the 24 are in `351882b2`), while L1 has 18 tagged bullets of ~500 (status regex; matches the plan's 4%) and one `Rejected:` bullet (`~/Documents/Invences/Hackathons/breaking_barriers_aws/memory/hackathon/strategy-and-ideas.md:64`). Moving these duties from rule to script is a near-certain gain.
- Phase 2.1/2.3/2.5 (ranked, chunked, capped, date-grouped retrieval). IDF fixes the "refresh in 18 logs" drowning; date grouping fixes the Q3/Q12 supersession class; one tool with one output format raises adherence more than any wording.
- Phase 3 (shorter rules), 1.6 (one directive at start), 6 (regression gate).

**Won't, or less than claimed:**
- Phase 1.1 map lines "from Decisions bullets (bold phrase)". Only `gen_active.py` writes `- **X.** Y.`; the real logs (`sessions/2026-11-01_351882b2-event-kit-analysis.md`, `…54a2594a-teacher-student-swarm.md`) use plain bullets. As specified, it is fitted to the generator.
- Phase 1.3 routing "to the topic file named in `Related:`". Real `Related:` lines name 1–7 files (dashboard log: 7), so most rejections land in `decisions/rejected.md`, a catch-all nothing routes to.
- Phase 2.2 `--alt` phrasings and 4.2 `Replaces:` are conventions Claude must remember: the failure mode the plan exists to escape.
- Phase 5.1 "the fact's own key terms return it in top 5" is self-referential; BM25 passes it trivially.

## 2. Flaws and risks

- **Wrong attribution.** `cortex_hook.py` snapshots the whole `memory/` tree per session, so the per-Stop diff includes other chats' edits; auto-tags (1.2) would stamp another chat's bullet with this chat's id. Attribute from this chat's own transcript JSONL `tool_use` entries (Edit/Write with a `memory/` path): exact chat, exact line.
- **Dangling anchors.** `(id8 L<n>)` points at transcripts that `cleanupPeriodDays` deletes. The log is the durable layer: primary anchor `sessions/<file>#heading`, transcript line secondary.
- **Stop `additionalContext` forces a continuation turn** (Claude Code hooks docs), so every lint nudge costs a model turn; rate-limiting is load-bearing.
- **The lock won't work.** `memory/.lock` cannot bind Claude's Edit tool in another chat. Use ownership instead: files only the hook writes (`MAP.md`, `sessions/README.md`, `*/_index.md`, atomic temp+rename) and files only Claude writes (`INDEX.md` "Where we are", topic bodies). Never both in one file.
- **Runtime.** `snapshot()` already rglobs and counts every file per Stop; a BM25 rebuild per Stop misses <1 s on 720 logs without an mtime-keyed index cache.
- **Recall can get worse** if TF-IDF picks "distinctive" tokens (`Torrey`, `LeCTR`, `Omidshafiei` in 54a2594a) over the query-likely phrases ("action advising", "advice budget") the curated line carries today.

**Open questions:**
1. *Auto-tag honesty:* chat-only `(auto id8 → log#heading)`; a line number only when read from the transcript tool_use position, never estimated; visibly a different class from Claude-verified tags.
2. *Generated vs curated:* no TF-IDF. Generate from Claude-written prose that already exists (Summary sentence, Decision/Rejected bullets, exchange headings) plus an optional `Keywords:` line; migrate every current curated map line into its log's `Keywords:` so `guarantees.py` still passes. The 14/14 claim never tested this: the generator's own maps were mechanical and Q6 sat in `sessions/README.md:354`; no per-arm scores exist in the scratchpad.
3. *Replace grep:* yes, in the rules; grep stays as a fallback in the reference only.
4. *Lock:* ownership split, not a lock (above).

## 3. What's missing

- **UserPromptSubmit hook running `cortex_search` on the prompt**, injecting the top 3–5 Decision/Rejected chunks (score threshold, ≤300 tokens). This makes "check before acting / never re-propose a rejected option" deterministic. The single largest lever, unused.
- **PostToolUse hook on Edit/Write under `memory/`**: lint the write at once (missing tag, missing `(L a-b)`, log >300 lines, write to a generated file) with exact attribution, instead of at Stop.
- **Alias file learned deterministically**: mine `recall miss:` changelog lines and `Keywords:` into `memory/aliases.md` ("keyword scoring = BM25 = lexical"); search expands from it. Keeps the Q6 bridge without `--alt`.
- **Diff-based supersession**: when a topic-file line is replaced in place, the hook moves the old line into `## History` with a date. No `Replaces:` convention.
- **Search output hygiene**: a "no hits above threshold" line (Q14 must say "not in memory") and hits wrapped as quoted data (Q13 injection).

## 4. The token belief

Partly right. Cached prompt tokens are cheap in dollars; attention is not, and the AGENTS.md finding the plan cites (overviews didn't speed navigation) says the always-loaded map is not where accuracy comes from. Growing L0 to 3–7k buys little once search is good.

Budget: rules ≤1.0–1.2k tokens (~60 lines; Recall-line spec and switch matrix leave); L0 memory ≤2.5k, ceiling 3k ("Where we are" ≤8 bullets, map ≤40 lines); hook injections ≤300 tokens per event. Total ~4k, under today's 4.7k, with unlimited growth in the searchable layers.

## 5. Order and scope

Ship: (1) Phase 0 plus a search eval harness with held-out questions on a copy of the real project, so "may only go up" is measurable from day one; (2) `cortex_search.py`: BM25, date grouping, alias expansion, threshold, quoting; (3) transcript-attributed auto-tags, rejected filing, ledger sync, and the UserPromptSubmit/PostToolUse hooks; (4) generated `MAP.md` and `sessions/README.md` under the ownership split; (5) rules slim-down, last, because the rules point at the scripts; (6) Phase 4 verify and diff-based history; (7) Phase 5 as `/cortex selftest` only.

Cut: TF-IDF nouns, `Replaces:`, embeddings, `measure.py` (status already reports rules/memory tokens and tag share), the hook-run retrieval self-check, the "messy variant" generator (use the real project).

Smallest version with most of the gain: (1)+(2)+(3) plus a ~1k-token rules file.

## 6. Acceptance criteria (measured on the real project or real chats, never on `gen_active.py` output)

1. **Held-out recall:** 20 questions written by a reviewer who hasn't seen the ranker, from session-log bodies, ≥6 sharing no content tokens with the stored fact; `cortex_search` puts the answer chunk in the top 5 for ≥16/20, and v6 ≥ v5 on the same set.
2. **Rejection probes:** 10 prompts re-proposing a stored rejected option in new wording; a fresh v6 chat names the rejection and its reason in ≥8/10 (v5 baseline recorded first).
3. **Honesty needles:** 5 never-stored questions → "not in memory" 5/5; a planted instruction in a log is never followed, 5/5 runs.
4. **Real-use compliance after Nov 3, 5 chats:** of bullets and headings added after the v6 install (diff against a pre-install snapshot), ≥95% of L1 bullets tagged (today 4% overall) and ≥95% of exchange headings line-ranged; ledger live end within 50 lines of the transcript at each chat's end; no auto-tag attributed to a chat whose transcript shows no edit of that file.
5. **Nothing lost:** `guarantees.py` passes between consecutive maintenance runs; every curated noun of today's `INDEX.md` is present in the generated maps after migration.
6. **Concurrency:** two chats editing memory for 10 turns each, zero lost or clobbered lines; the hook never writes a Claude-owned file.
7. **Cost and runtime:** rules ≤1.2k and L0 ≤3k tokens as reported by status; Stop hook p95 <1 s on the 720-log corpus and the real project; zero hook errors in 50 turns.
8. **Supersession:** for the two real stale→corrected facts (`brief.md` "no 2026 rubric" → `event-kit.md`; frontier-teacher tier → peer teaching), search output shows old → new in date order.
