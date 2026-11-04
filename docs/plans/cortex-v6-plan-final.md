# CORTEX v6: final plan (after Fable's review)

Principle: Claude writes content and makes judgment calls; hooks and scripts enforce every mechanical duty. Rules shrink; searchable memory grows without limit; what reaches Claude per message is chosen by relevance, not loaded wholesale.

## Step 1 · Measure first (eval harness + honesty)
- Fix README/guide overclaims (rules 2.7k not 1.8k, five scripts not three, real per-chat cost).
- `tests/`: deterministic suite (hook states, Python 3.9, nothing-lost guarantees) and a **search eval** on a copy of the real project: 20 held-out questions written from log bodies by someone who hasn't seen the ranker, ≥6 sharing no words with the stored fact; plus the synthetic 720-log project for scale. Record the v5 baseline before anything changes.

## Step 2 · `cortex_search.py`: one ranked search over all memory
- BM25 over chunks (topic-file bullets, session-log exchanges, Decisions/Rejected bullets, map lines), mtime-keyed index cache so it stays < 1 s.
- Date-grouped results: hits on the same subject in date order, newest marked, so "old → new" is visible.
- **Alias expansion learned by code:** `memory/aliases.md` mined from `Keywords:` lines and `recall miss:` changelog entries ("keyword scoring = BM25 = lexical"), so paraphrases bridge without Claude remembering to pass synonyms.
- Hygiene: a score threshold that prints "no match in memory" (never-stored questions), hits wrapped as quoted data (planted instructions stay data), output capped to the best ~40 lines, exact sources/lines/layers counted for the recall line.
- **RAG (embeddings), as a measured experiment:** optional local model (no server, nothing leaves the machine) added as a third signal in a hybrid ranker, switched on only if the held-out eval shows it beats BM25 + aliases on no-shared-word questions without hurting exact identifiers.

## Step 3 · Hooks that make the rules true
- **UserPromptSubmit (new):** runs `cortex_search` on each message; injects the top 3–5 Decision/Rejected/fact chunks above threshold (≤300 tokens, quoted, silent). Makes "check before acting / never re-propose a rejected option" deterministic.
- **PostToolUse on Edit/Write under `memory/` (new):** lints each memory write the moment it happens, with exact attribution from the transcript: missing source tag → added by code as `(auto <id8> → sessions/<log>#<heading>)`, a distinct, durable class (log anchor, not a transcript line that expires); exchange heading without `(L<a>-<b>)` → line range filled from the transcript position; log over 300 lines → split; write to a script-owned file → reverted with a message. Feedback lands in the same turn, no extra continuation turn.
- **Stop:** rejected options filed into topic files (owner chosen by best search match of the rejected text against topic files, not by the 1–7-file `Related:` line; ties → the log's primary topic); ledger synced from the log's own `(L<a>-<b>)` claims; the synced pulse stays. Rate-limited, at most one judgment nudge.
- **Supersession by diff:** when a topic-file line is replaced in place, the hook moves the old line into that file's `## History` with its date. No convention to remember.
- **SessionStart:** one directive at most (recovery), consolidation silent, self-test never before the first answer.

## Step 4 · Generated maps under an ownership split
- Script-owned (atomic temp+rename, Claude never edits): `memory/MAP.md` (full hierarchical map: per-folder files, recent logs, week/month/quarter rollups), `sessions/README.md`, `*/_index.md`, `aliases.md`.
- Claude-owned (the hook never writes): `INDEX.md` "Where we are", topic-file bodies, session logs, preferences.
- Map lines generated from prose Claude already writes: Summary sentence, Decision/Rejected bullets (plain or bold), exchange headings, plus an optional `Keywords:` line. No TF-IDF noun guessing. Migration copies every curated noun in today's INDEX.md into `Keywords:` so nothing is lost (checked by `guarantees.py`).

## Step 5 · Rules slim-down (last, because they point at the scripts)
- Rules ≤ ~1.2k tokens (from 2.7k): storage test, where things go, trust order, use `cortex_search`, reading-off/off, a short recall line fed by the script's counts, silence.
- Always-loaded memory ≤ ~2.5k (ceiling 3k): "Where we are" + a compact folder-level map (≤ 40 lines). The detailed hierarchical map lives in `MAP.md` and reaches Claude through search and per-message injection.

## Step 6 · Correctness
- `cortex_verify.py`: `(code: path:line)` facts checked against the repo; facts naming paths, commands or ports grepped; status age. Status and the recall line take `unverified`/`stale` from this.
- No LLM rewrites of whole memory files; consolidation is scripted, Claude edits single bullets.

## Step 7 · Self-test
- `/cortex selftest` only (LLM paraphrase quiz, saved scores and transcripts). The automatic hook-run check is dropped (it was self-referential).

## Acceptance criteria (on the real project / real chats, never on generator output)
1. Held-out recall: answer chunk in top 5 for ≥16/20 questions; v6 ≥ v5 on the same set.
2. Rejection probes: 10 re-worded re-proposals of stored rejected options → a fresh v6 chat names the rejection and why in ≥8/10 (v5 baseline recorded first).
3. Honesty: 5 never-stored questions → "not in memory" 5/5; a planted instruction never followed, 5/5.
4. Real-use compliance over 5 chats after Nov 3: ≥95% of new topic-file bullets tagged, ≥95% of new exchange headings line-ranged, ledger within 50 lines of the transcript at chat end, zero mis-attributed auto-tags.
5. Nothing lost: guarantees pass between maintenance runs; every curated noun of today's INDEX.md present after migration.
6. Concurrency: two chats editing memory for 10 turns each, zero lost or clobbered lines; hooks never write a Claude-owned file.
7. Cost/runtime: rules ≤1.2k and L0 ≤3k tokens; hook p95 < 1 s on 720 logs and the real project; zero hook errors in 50 turns.
8. Supersession: the two real stale→corrected facts show old → new in date order.

## Cut
TF-IDF noun selection, `Replaces:` convention, `--alt` phrasing convention, hook-run retrieval self-check, `measure.py`, the synthetic "messy" generator (use the real project instead).
