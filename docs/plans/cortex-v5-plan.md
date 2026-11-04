# CORTEX v5 plan: keep L0 small without losing recall

Skill source: `~/Developer/cortex/skills/cortex/` (git repo `~/Developer/cortex`, also installed at `~/.claude/skills/cortex/`).
Real project using it: `~/Documents/Invences/Hackathons/breaking_barriers_aws/` (live hackathon, judging 2026-11-03; must not be touched until reviewed, A/B-tested and approved by the user).

## Goal (user's words, paraphrased)
L0 (what loads in every chat) is filling its ~3k-token budget. Fix that so CORTEX gets *smarter*, never dumber: it must still find old and subtle information, stay foolproof, and surface information when it matters.

## Measured L0 in the real project (tokens ≈ bytes/4)
| Part | Tokens |
|---|---|
| CORTEX rules block inside project `CLAUDE.md` (from `reference/claude-block.md`) | 1,328 |
| `INDEX.md` L1 topic table (16 rows, columns File / Covers / Load when) | 521 |
| `INDEX.md` L2 session-log table (8 rows, File / Date / Covers) | 314 |
| `INDEX.md` "Where we are" (8 bullets) | 254 |
| `team/user-preferences.md` | 409 |
| **Total** | **2,845 of 3,000** |

## Options already ruled out
- **Moving the writing rules to `PROTOCOL.md`, read on demand:** in `auto` mode nearly every chat writes, so Claude would read it every chat anyway. No saving, plus risk of skipping the read.
- **Injecting rules through the SessionStart hook:** works only with hooks installed; replaced by the `@` import below.

## The plan
1. **Shared, shorter rules file.** Rewrite the block as `reference/rules.md` inside the skill, about 650 tokens, same behaviour. Each project's `CLAUDE.md` gets a small stub instead of the full block:
   ```
   <!-- CORTEX:BEGIN v5 -->
   ## Project memory (CORTEX) · skill: ~/.claude/skills/cortex
   @~/.claude/skills/cortex/reference/rules.md
   @memory/INDEX.md
   @memory/team/user-preferences.md
   <!-- CORTEX:END -->
   ```
   Claude Code docs (code.claude.com/docs/en/memory): `@` imports may use `~/` paths; imports outside the project trigger a one-time approval dialog; if declined, the imports stay disabled. Fallback: `/cortex config rules=inline` copies the rules into the block as today.
   Per-project values in the old block move: `{{IANA_TZ}}` to the index's line 2; `{{TOPIC_ROUTING}}` is replaced by the index's routing section (step 3).
2. **Separate budgets.** Rules: fixed, target ≤ ~700 tokens. Memory L0 (`INDEX.md` + preferences): grows, target ≤ 2,000 tokens. `/cortex status` shows both, measuring what is really loaded by following the `@` imports in the block.
3. **Slimmer index.**
   - **L1 routing by folder:** one line per folder, listing each file with its trigger words (keeps file-level "Load when"; drops the "Covers" column, since each L1 file's `Summary:` line already says what it covers). Example: `` `hackathon/` brief (event, tracks, judges, timing) · event-kit (AWS build, scoring, deadlines) · … ``. A folder with more than ~6 files gets its own `_index.md`, and L0 lists only the folder.
   - **Session-log table out of L0:** moved to `memory/sessions/README.md` (one line per log: file, date, covers). L0 keeps one pointer line. Route to history via L1 source tags `(id8 Lnnn)` → log filename contains id8 → grep. **Open question for reviewers: is this safe for "why did we…" questions, or should L0 keep a compressed one-liner per recent log?**
   - **"Where we are":** ≤ 8 dated bullets; a bullet not touched in 14 days is demoted into its owning L1 file's `Summary` or body (write-back, never deleted).
   - **Preferences:** cap ~400 tokens; over cap, area-specific preferences move to the L1 file of that area with a pointer.
4. **Self-cleaning.** When memory L0 passes 85% of its budget, the SessionStart hook adds an instruction to run the consolidation procedure (new section in `PROTOCOL.md`) before other work; `/cortex status` shows the same warning without hooks.

## Rule-by-rule mapping (old block → v5)
Old block: `reference/claude-block.md`. Every rule must survive (in `rules.md`, always loaded) unless it is needed only at an event that already has a trigger.

| # | Old rule (section) | v5 location |
|---|---|---|
| R1 | Always load INDEX + preferences (header) | stub imports |
| R2 | Layer definitions L0/L1/L2/raw (header) | rules.md, one line each |
| R3 | `/cortex help`; meaning of the hook's `CORTEX:` line (header) | rules.md |
| R4 | Recording modes auto/manual/paused; remind once if paused (§1) | rules.md |
| R5 | Recover unlogged tails first, extractor command, extend ledger, never touch active chats (§1) | rules.md (short); the hook's `CORTEX:` line carries the exact command with the real skill path |
| R6 | Never read excluded/skipped/paused ranges (§1) | rules.md |
| R7 | Pick 1–3 L1 files by "Load when"; check `Summary:` (`head -4`) first (§2) | rules.md (triggers now in folder routing) |
| R8 | L1 read whole; session logs and changelog only by grep + ±25-line windows (§2) | rules.md |
| R9 | Which layer answers what (4 mappings) (§2) | rules.md |
| R10 | Raw chats last resort via `ledger_scan.py --grep`, extractor ±20; never grep `.jsonl` (§2) | rules.md |
| R11 | Stop when answered; verify system facts read-only in code; ≤4 memory files beyond L0, else fix the index (§2) | rules.md |
| R12 | Trust order (code > user's latest > sourced L1 > unsourced L1 > session log > compaction summary); cite (§2) | rules.md |
| R13 | On conflict: act on trust order, fix stale file same turn, changelog line (§2) | rules.md |
| R14 | Don't re-read L0 (§2) | rules.md |
| R15 | Write only while recording, in the same turn (§3) | rules.md |
| R16 | Storage test; store even if no category; examples in PROTOCOL (§3) | rules.md |
| R17 | Subtle details to the session log when in doubt (§3) | rules.md |
| R18 | Drop noise; memory-system work = one changelog line (§3) | rules.md |
| R19 | Session log: create from template at first write, add ledger row, announce path, headings end `(L<a>-<b>)` (§3) | rules.md |
| R20 | Same turn: ledger live end = `wc -l`; never across a pause; never mark unlogged lines (§3) | rules.md |
| R21 | Current-truth change → edit the one owning L1 file with a source tag; no tag = unverified (§3) | rules.md |
| R22 | Changelog one-liner at notable events (§3) | rules.md |
| R23 | Where things go: topic routing; prefs one line each; status → "Where we are" ≤8 bullets (§3) | rules.md + index routing section |
| R24 | One fact one place; edit in place; absolute dates; no secrets/contact data; no auto-memory for project facts (§3) | rules.md (timezone read from index line 2) |
| R25 | Checkpoint triggers and 5 steps (§4) | rules.md |
| R26 | Telemetry lines `⟦CORTEX⟧`, only for real actions, off with `Logs: off` (§5) | rules.md, one generic format |
| R27 | Caps, rollovers, templates, audit in PROTOCOL.md (footer) | rules.md pointer; PROTOCOL gains §Consolidation and §Routing format |

## Verification planned
- A/B cold-start test on a copy of the real project: one fresh subagent with the old L0, one with the new, same questions (what/where it stands, how to run, why a real decision was made, plus a deliberately old/subtle fact from an Oct 25 session log). New must answer at least as well.
- Diff of the real project's files shown to the user before applying.

---
## Outcome (2026-11-02), after two reviews and an A/B recall test

What changed from the plan above:
- **Rules delivery:** not an `@~/` import. Reviewer B showed the external import fails silently when its approval dialog is declined, in headless runs and with project-local installs. Rules are copied into each project as `memory/RULES.md` and imported relatively; `/cortex status` checks the copy against the skill's and `/cortex upgrade` refreshes it.
- **Rules size:** grew from 1,328 to ~1,690 tokens instead of shrinking to ~650: every protected rule kept, plus check-before-acting, rejection capture, map maintenance, re-reading the index while another chat is live, and the budget rule.
- **Session-log table:** kept in L0 (Reviewer A: 0 of ~534 L1 bullets carry line-level source tags, so the planned tag→log route didn't exist). Each line now names topics, decisions and rejected options; ≤10 newest, older to `sessions/README.md`.
- **Topic map:** folder lines that keep every noun from the old Covers and Load-when columns.
- **Budget:** a 2,000-token memory budget tripped at 85% immediately after upgrade. Replaced by structural caps (≤8 bullets, ≤10 logs, ≤6 files per folder, ≤40 preference lines) as the trigger, with a 3,000-token ceiling measured as the size at every cap.
- **Net L0 on the real project:** 2,845 (v4) → ~3,400 tokens (v5): bigger today, bounded by construction.
- **A/B recall test** (one fresh agent per version, five questions incl. two rejected options and an Oct 25 detail): v5 answered all five correctly, as v4 did; v5 was better on Q4 (read the 2026 kit) partly because the 4-file cap is now explicitly per question. n=1 per arm.
- **Track 1 bug fixes** (pause detection, Python 3.9, DST, corrupt state files, range parsing, project root, hook timeout, backup location) shipped and installed separately.
