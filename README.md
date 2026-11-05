# 🧠 CORTEX

**Project memory for Claude Code that doesn't forget: every chat archived and searchable, decisions tracked with their reasons, and the exact source one call away.**

Claude Code is stateless between chats. CORTEX gives each project folder a memory that every chat in it shares:

- a **curated core** that loads at the start of each chat (status, map, preferences);
- **records**: typed, dated decisions, rejections, facts and relations, each with the chat and transcript line it came from, and old → new chains when something changes;
- the **chat archive**: the redacted text of every recorded chat, line-addressed, so no detail is lost even after Claude Code deletes old transcripts;
- **native memory tools** (`memory_search`, `memory_open`, …) and **hooks** that capture, archive, inject and re-anchor memory without being asked.

It runs locally: Python 3.9+ standard library and SQLite (FTS5), a small local MCP server for the tools, no embeddings, no cloud service. Memory is plain files you can read, `grep` and `git diff`.

> 📖 **[Open the user guide](skills/cortex/guide/cortex-user-guide.html)**: an illustrated walkthrough of the layers, the features and every command. Download it and open it in your browser.

---

## 🆕 New in v8, and how to use each feature

| Feature | What it does for you | How to use it |
|---|---|---|
| 🗂️ **Total recall** | Every recorded chat is archived (secrets and emails masked) and searchable down to the transcript line. Details that records and notes left out are still there. | Automatic. Search finds archive passages too; open any with `memory_open "<chat> L<a>-<b>"`. |
| 🎯 **Pinpoint search** | One call returns the current decisions, rejected options, old → new chains and the exact passages, each with a pointer, a snippet and a match strength (strong / partial / weak). | Claude calls `memory_search` itself. You can run `/cortex recall <question>`. |
| 🧰 **Native memory tools** | Claude gets real tools (no Bash permission prompts): `memory_search`, `memory_open`, `memory_timeline`, `memory_brief`, `memory_record`. | Installed by `./install.sh` (registers the local MCP server). |
| ☕ **Catch-up brief** | A new chat starts knowing what changed since your last session in this project: new decisions, rejections, status changes, open items. | Automatic at session start. On demand: `/cortex brief [since DATE]`. |
| 📡 **Live cross-chat updates** | Running two chats on one project? When one records a decision, the other hears about it with your next message. | Automatic (inject hook). |
| ⚓ **Survives compaction** | After Claude Code compacts a long chat, CORTEX puts back what this chat decided, rejected and left open. | Automatic (SessionStart after compaction). |
| 🕰️ **Timeline** | One subject's whole history, old → new: what was decided, what replaced what and why. | `/cortex timeline <subject>` or `memory_timeline`. |
| 📌 **Open items** | Every unanswered question and pending proposal, oldest first, ready to settle. | `/cortex open-items`. |
| 📜 **Decision log** | `memory/DECISIONS.md`: every decision and rejection with its reason, date and source; replaced ones struck through. Shareable in a pull request. | `/cortex decisions`. |
| 🔍 **Stale check** | Records that name code files which changed or vanished since are flagged in search results and listed on demand. | Automatic flags; `/cortex verify` for the full list. |
| 🚫 **Rejected-option guard** | When you ask about something that was rejected, the rejection and its reason arrive first. | Automatic (inject hook). |
| 🛡️ **Injection-aware** | Retrieved text is quoted as data; items that contain instruction-like text are flagged and never injected. | Automatic. |
| 🔒 **Privacy follows the ledger** | Excluded chats are never archived (and their archive is deleted); skipped or paused ranges are never copied and are removed if skipped later; nothing is saved while CORTEX is off. The archive is git-ignored by default. | `/cortex exclude`, `/cortex pause`, `/cortex off`, `/cortex forget`. |
| ⬆️ **One-step upgrade** | Moves a v5 or v7 project to v8: backup, records from past chats (v5), archive, index, rules. | `/cortex upgrade` (shows a dry run first). |

Everything from earlier versions stays: start / pause / resume / off / on, exclude / include, forget, the coverage ledger, `/cortex all` backfill, status, audit, self-test.

---

## 🧬 How it works

**Storage, three layers with one source of truth each.**
1. **Curated core** (`memory/INDEX.md`, topic files, session logs, preferences): written by Claude, read whole, always loaded in part. Small by construction.
2. **Records** (`memory/records.jsonl`): append-only, one typed item per line (`decision`, `rejection`, `fact`, `status`, `open`, `lesson`, `preference`, `relation`) with `valid_from`, `supersedes` and `source {chat, line}`. Written only through `cortex_write` / `memory_record`, which refuses silent duplicates and asks whether a conflicting item replaces or coexists with the old one. A background extractor (Haiku) records each substantive turn, and a backfill builds records from past chats.
3. **Chat archive** (`memory/chats/<chat>.txt`): the readable, redacted text of every recorded chat, each block tagged with its line in the original transcript. Raw text is the stored value; records are pointers into it.

**Retrieval, one deterministic pipeline (~70 ms).** An incremental SQLite FTS5 index covers records, note chunks and archive passages. Each passage is also indexed under the facts drawn from its lines ("facts as keys"). BM25 ranks the question and Claude's alternative wordings, fused by reciprocal rank; records about the subjects the question names are boosted. The answer pack is **coverage-aware**: records first, then passages that add lines the records don't already cover, without near-duplicates, each with a pointer and a query-focused snippet. A subject graph with Personalized PageRank exists as an opt-in re-ranker (`CORTEX_PPR=1`); it did not help on held-out questions, so it is off.

**Hooks.** `SessionStart` (orientation, catch-up brief, archive catch-up, re-anchoring after compaction) · `UserPromptSubmit` (relevant memory and other chats' news, ≤ ~400 tokens) · `PreToolUse` / `PostToolUse` (protect script-owned files, add provenance, lint) · `Stop` (archive the chat, capture records in the background, logging nudge). All are silent outside CORTEX projects, and the v8 ones stay silent in projects still on v5.

---

## 📊 Measured, not claimed

Tested on a real project (7 chats, 6,107 transcript lines) with questions written by separate agents that saw only the transcripts. Gold evidence lines were never shown to the builder. Raw results stay local because they contain private project text; the tools to reproduce them are in `tests/tools/`.

**Retrieval** (share of the lines each answer comes from that appear in the result pack; strict ±3 lines; no LLM judge involved):

| | v7 search | v8 search |
|---|---:|---:|
| 90 held-out questions, all | 0.531 | **0.609** (+7.8 pts) |
| held-out, relational (60) | 0.468 | **0.561** (+9.3 pts) |
| held-out, finds ≥1 source line | 0.789 | **0.856** |
| 64 development questions | 0.627 | **0.746** |

**Answer accuracy** (Claude Sonnet answering, majority-of-3 per-fact judge, 2 runs per arm): see the table filled in by the latest run below.

ANSWER_TABLE_PLACEHOLDER

**What didn't work, published on purpose:**
- **The graph:** typed relations plus Personalized PageRank never beat plain ranking on held-out questions. It's off by default.
- **Records-first v7:** it scored below curated v5 on unseen questions (0.792 vs 0.828, not significant). That's why v8 makes the raw archive the stored value and records the index.
- **"Facts as separate documents"** hurt retrieval (it matches LongMemEval's finding). Facts work as keys on the raw passage.
- **The first judge was the main error source:** it marked complete answers partial. It was rebuilt as per-fact grading, majority of 3.
- **Statistical power:** 90 questions only resolve differences of about 8 points. Smaller differences above are directional, not proven.

---

## 🚀 Install

**Requirements:** [Claude Code](https://claude.com/claude-code) and Python 3.9 or newer as `python3` (with SQLite FTS5, which standard builds include).

```bash
git clone https://github.com/arth17singh/cortex.git
cd cortex
./install.sh
```

That copies the skill to `~/.claude/skills/cortex` and offers to register the hooks and the memory tools. Other options:

```bash
./install.sh --hooks            # skill, hooks and memory tools without prompting
./install.sh --no-hooks         # skill only
./install.sh --link             # symlink instead: `git pull` here updates the skill everywhere
./install.sh --project          # install into this project only (./.claude/, project-scoped tools)
./install.sh --uninstall-hooks  # remove the hooks and the memory tools again
```

An existing install is moved to `cortex-backups/cortex.bak-<timestamp>`, never overwritten. `settings.json` is backed up before any change, and other hooks are left alone. By hand: merge [`hooks/settings-snippet.json`](hooks/settings-snippet.json) into `~/.claude/settings.json` and run `claude mcp add --scope user cortex -- python3 ~/.claude/skills/cortex/scripts/cortex_mcp.py`.

### Updating and upgrading projects

```bash
cd cortex && git pull && ./install.sh --hooks
```

Then run `/cortex upgrade` once in each project. It shows a dry run (chats, lines, estimated model calls), backs up `memory/`, and moves the project to v8. A v7 project takes seconds; a v5 project needs a backfill of records from its past chats, which takes minutes. Projects you don't upgrade keep working as before.

---

## ⚡ Quick start

```text
/cortex start                 # record this chat from now on (builds memory/ on first run)
/cortex all                   # backfill past chats that aren't tracked yet
/cortex recall why did we pick Postgres over DynamoDB?
/cortex brief                 # what changed lately, across every chat
/cortex timeline auth service # one subject's history, old -> new
/cortex open-items            # questions and proposals still waiting for a decision
/cortex decisions             # write memory/DECISIONS.md
/cortex status                # coverage, settings, size, next suggested action
```

---

## 🧰 Commands

| Command | What it does |
|---|---|
| `/cortex help` | Lists the commands, with a short status line |
| `/cortex upgrade` | Moves a project to v8 (dry run first, backs up, refuses while another chat is open) |
| `/cortex start [--from-chat-start]` | Records this chat from now on (or from its first line) |
| `/cortex all [options]` | Backfills untracked past chats; safe to re-run. Options: `only <chat>`, `since DATE`, `last N`, `exclude X`, `include-skipped`, `--yes` |
| `/cortex recall <question>` | Answers from memory with exact pointers, quotes and match strength |
| `/cortex brief [since DATE]` | Catch-up: what changed across every chat (default: last 3 days) |
| `/cortex timeline <subject>` | One subject's history, old → new, with reasons and pointers |
| `/cortex open-items` | Unresolved questions and proposals, oldest first |
| `/cortex decisions` | Renders the decision log `memory/DECISIONS.md` |
| `/cortex verify` | Records naming code files that changed or vanished since they were recorded |
| `/cortex status` | Coverage, settings, memory size against budget, warnings |
| `/cortex save [note]` | Full checkpoint, or a note even when paused |
| `/cortex pause` / `resume` | Stops or restarts **saving** (this chat, or `--project`). Memory is still read |
| `/cortex pause --read` / `resume --read` | Stops or restarts **reading** from that point on; the chat is still saved |
| `/cortex off` / `on` | Turns CORTEX off entirely from that point on: no reading, no saving, no archiving |
| `/cortex exclude <chat>` / `include <chat>` | Permanently leaves a chat out of memory (and its archive), or puts it back |
| `/cortex forget <topic>` | Finds every mention (records, notes, archive), shows exact deletions, keeps it from coming back |
| `/cortex audit` | Checks memory is consistent, not duplicated and within its caps |
| `/cortex selftest` | Quizzes memory on recent decisions with a fresh agent, and repairs every miss |
| `/cortex config [key=value]` | `recording`, `commit`, `timezone`, `exclude-default`, `logs`, `rules`, `selftest`, `hooks` |

### Native tools (what Claude calls)

| Tool | Purpose |
|---|---|
| `memory_search(question, alternatives?)` | Records, rejected options, changes and archive passages, with pointers and match strength |
| `memory_open(pointer)` | The exact words behind a pointer (`"<chat8> L<a>-<b>"` or `"<file>:<line>"`) |
| `memory_timeline(subject)` | One subject's history |
| `memory_brief(since?)` | What changed lately across all chats |
| `memory_record(type, subjects, statement, why?, …)` | Record a decision, rejection, fact, … (dedupe and conflict checks included) |

---

## 📁 What's in this repo

```
cortex/
├── install.sh                       installer (copy / --link / --project, hooks + memory tools)
├── hooks/
│   ├── settings-snippet.json        the hook entries, ready to merge
│   └── install_hooks.py             safe, idempotent merge/remove into settings.json
├── skills/cortex/
│   ├── SKILL.md                     every /cortex subcommand's behaviour
│   ├── guide/cortex-user-guide.html illustrated user guide
│   ├── reference/                   rules.md (v8), rules-v5.md, CLAUDE.md block, hooks-v8.json, mcp.json, templates
│   └── scripts/
│       ├── cortex_search.py         the search: pack, pointers, --open, match strength
│       ├── cortex_index.py          incremental SQLite FTS5 index + subject graph
│       ├── cortex_archive.py        redacted, line-addressed chat archive
│       ├── cortex_mcp.py            the native memory tools (local MCP server, stdio)
│       ├── cortex_tools.py          brief, timeline, open-items, decisions, verify, live updates, re-anchoring
│       ├── cortex_write.py          the only write path for records
│       ├── cortex_capture.py        Stop hook: archive + background record capture
│       ├── cortex_inject.py         UserPromptSubmit hook: relevant memory + other chats' news
│       ├── cortex_guard.py          PreToolUse/PostToolUse: ownership, provenance, lint
│       ├── cortex_hook.py           SessionStart/Stop: orientation, catch-up, re-anchor, nudges
│       ├── cortex_backfill.py       records from past chats (Haiku, background), with conflict judging
│       ├── cortex_upgrade.py        v5 / v7 → v8 migration
│       ├── cortex_lib.py, cortex_render.py, ledger_scan.py, extract_transcript.py, cortex_status.py, selftest.py
└── tests/tools/                     the evaluation harness (runner, per-fact judge, retrieval check, arm builder)
```

---

## 💡 Good to know

- **The archive is local and git-ignored.** `memory/chats/` and `memory/.cache/` each carry their own `.gitignore`. Secrets and email addresses are masked when chats are archived.
- **Transcripts expire, the archive doesn't.** Claude Code deletes old transcripts after `cleanupPeriodDays` (30 by default). CORTEX archives each chat as it goes, so set that up early in a project.
- **Background model use is small:** one Haiku call after substantive replies in v8 projects (capture), and a one-time backfill on upgrade from v5. Search itself never calls a model.
- **`/cortex` is user-invoked only.** The skill sets `disable-model-invocation`; Claude uses the memory tools on its own.
- **Uninstall:** `./install.sh --uninstall-hooks`, delete `~/.claude/skills/cortex`, and remove the CORTEX block from your project's `CLAUDE.md` (between `<!-- CORTEX:BEGIN -->` and `<!-- CORTEX:END -->`). Your `memory/` folder is yours to keep or delete.

---

## 📄 License

[MIT](LICENSE)
