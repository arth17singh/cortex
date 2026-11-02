# 🧠 CORTEX

**A tiered, self-auditing memory architecture for Claude Code.**

Claude Code is stateless between chats. CORTEX adds the missing layer: a hierarchical, provenance-tracked project memory with a coverage ledger, hook-driven capture and an always-loaded part that is bounded by construction. Claude opens every session already oriented, with decisions, rationale, conventions and open threads in context, without paying for them in context window.

It's a single skill: markdown, three stdlib-only Python scripts and two hooks. It has no dependencies, no server, no vector database and no embeddings. The memory is plain markdown, so you can read it, `grep` it and `git diff` it.

> 📖 **[Open the user guide](skills/cortex/guide/cortex-user-guide.html)**: an illustrated walkthrough of the layers, the ledger and every command. Download it and open it in your browser.

---

## 🧬 Architecture

CORTEX is built around six ideas.

### 1. Tiered memory, bounded by construction
Memory is a hierarchy, and each tier has a defined job, a size cap and a retrieval rule:

| Tier | Where | Role |
|---|---|---|
| **L0** | `memory/RULES.md` + `memory/INDEX.md` + preferences, imported by a 6-line stub in `CLAUDE.md` | Always loaded: the rules, current status, and a detailed map of every topic file and recent session log |
| **L1** | `memory/<topic>/*.md` | Current truth. ~150 lines per file, every fact source-tagged |
| **L2** | `memory/sessions/*.md` | Per-chat history and fine detail. Searched by grep, read by window |
| **L3** | raw Claude Code transcripts | Ground truth. Reached only through the redacting extractor |

Retrieval goes top-down. Claude starts at the map, follows it to the right L1 file, and descends to L2 and L3 only when a question demands it.

**The map is deliberately detailed.** It is how Claude notices that memory covers a topic at all, so every topic file is listed with its distinctive nouns and the situations that should load it, and every recent session log with its topics, decisions and rejected options. Detail beats brevity here, so L0 is kept in check by structure rather than by trimming:

- **The rules** (`memory/RULES.md`, ~1.8k tokens) are a fixed cost. They ship with the skill, are copied byte-for-byte into each project (no approval dialog, no path dependency), and `/cortex upgrade` refreshes them, project by project.
- **The memory part is hierarchical**, so it scales with how active a project is without forgetting. History stays visible at decreasing resolution instead of falling off the map:
  - the newest 15 session logs each have their own line; older ones are covered by up to 4 **week** lines, then up to 6 **month** lines, then **quarter** lines. A rollup line is a size-limited index (≤600 characters for a week, ≤900 for a month) of rejected options, decisions with specific reasons, and distinctive topics. Every log's own line stays in `sessions/README.md`, one hop away;
  - a folder lists up to 10 topic files one by one; a bigger folder gets a **summary line** of its ~25 most distinctive nouns, and its per-file lines move to its `_index.md`;
  - ≤8 dated "Where we are" bullets, ≤40 preference lines, and a 7,000-token backstop for runaway lines.

  **Stress-tested** on a synthetic very active project (720 session logs over 90 days, 118 topic files) with 14 adversarial questions: paraphrased rejections, facts later reversed, near-duplicate names, an exact number from an old Q&A, a fact buried in yesterday's log, a question about something never stored, and an instruction planted inside a log. The flat layout used ~1.0k memory tokens and scored 12–13/14; it missed a 6-week-old rejection in both runs, because nothing on its map pointed to it. The hierarchical layout used ~4.3k tokens and scored 14/14, with every per-log and per-file line and all 1,251 nouns verified by script to still be in the maps. Unlimited rollups also scored 14/14 but used ~10.2k tokens. Every run ignored the planted instruction and said "not in memory" for the never-stored fact. These are single runs per layout, so read them as evidence, not proof.
- **Consolidation** runs when a cap is crossed: it moves detail one level down, leaves a pointer, backs up first, and never deletes. Open items and "never/always" preferences never move.

### 2. A coverage ledger: memory with accounting
`memory/LEDGER.md` records, per chat, exactly which line ranges are `live` (recorded as the chat ran), `skipped` (before you started), `paused`, `excluded` or still `backfill`.

- Claude marks a range as covered only after it has actually logged it, in the same step as the memory it describes.
- Ranges are never relabelled and a live range is never stretched across a pause, so the ledger can't overstate what memory holds.
- Backfill is incremental and idempotent. `/cortex all` works only on uncovered ranges, so you can run it as often as you like.
- Chats open in another window are detected and deferred, never mined mid-flight.

### 3. Hook-driven capture and recovery
Two hooks run the loop without you thinking about it:

- **`SessionStart`** injects a one-line state summary: this chat's id and transcript, the recording mode and any unlogged tails in other chats. Claude recovers those gaps first.
- **`Stop`** watches the distance between the transcript and the ledger. When it grows too large, it gives Claude a rate-limited nudge to checkpoint. The hook never writes the ledger itself.

A crashed, closed or abandoned chat therefore leaves a recoverable trace instead of a hole. Both hooks fail silent and do nothing in projects that haven't enabled CORTEX.

### 4. Provenance, privacy and consent as defaults
- **Provenance:** facts carry source tags (`<id8> L<line>`), and `/cortex recall` answers with `memory/<file>:<line>` citations, a confidence level and an explicit list of anything unverified.
- **Privacy:** a redaction pass strips API keys, tokens, passwords and cloud credentials before text reaches memory. It never stores anyone's email or phone number, and never opens `.env*` or credential files.
- **Consent:** anything that reads many chats, deletes memory or changes git, hooks or settings is shown to you first and waits for your OK.
- **Control:** pause per chat or per project, exclude a chat for good, or `forget` a topic. Forgetting purges every match and records the label, never the content, so the topic is not re-learned.

### 5. Memory that improves itself
CORTEX doesn't wait for you to maintain it. It learns from three signals, with no command needed:

- **Your corrections.** When you tell Claude "we already decided that" or "no, it's X", that is a recall miss. Claude fixes the fact, then fixes *why* memory missed it: a fact never stored gets stored, a fact the map couldn't reach gets its words added to the map. It costs nothing extra, because it happens in the turn where you corrected it.
- **Its own struggles.** If answering took more than 4 memory files, the map was missing something, so Claude adds the missing words. A rejected option found only in an old session log is copied into its topic file, so it's never proposed again.
- **An automatic self-test.** After 5 session logs have changed (at most once a day), the hook asks for a self-test. Claude turns recent decisions, rejected options and findings into questions, plus two facts from the oldest logs, so old and subtle material keeps being tested. A fresh background agent answers them with nothing but memory, and every miss is repaired at its cause. It says nothing in chat; the score shows in the `learning` row of `/cortex status`.

Learning only ever edits memory, never the rules, so every project keeps the same behaviour. `/cortex status` shows the self-test trend and how many corrections memory has learned from. `/cortex config selftest=off` stops the automatic test, and `/cortex selftest` runs one on demand.

### 6. Live status
You can see CORTEX working, without it getting in your way.

**At the start of every chat**, one line from the `SessionStart` hook. The bars are a 7-day sparkline of memory writes, so you can see at a glance whether memory is being kept up to date:

```
◉ CORTEX auto  ·  12 topics  ·  31 chats remembered  ·  ▁▃▅··█▂ 7d  ·  last write 2h ago  ·  ⚠ 1 unlogged tail, recovering  ·  /cortex status
```

**After a turn that changed memory**, a pulse naming exactly what was written. It is a before and after snapshot of `memory/`, so it never appears when nothing changed:

```
⟲ CORTEX synced  ·  L1 engineering/auth.md +6 · L2 2026-11-01_a1b2c3d4-auth.md +14  ·  ledger → 388
```

**Claude itself stays quiet about memory.** It never writes "Saved to memory" or "Session log: …" in a reply; the synced line already says what changed. It mentions memory only when something needs your OK, once per chat while recording is paused, when you run a `/cortex` command, or when it cites memory as the source of an answer.

**When memory changes an answer, you see it, and how much.** The one exception to the silence is a recall line at the end of a reply, written only when the answer depended on something you didn't say in this chat:

```
◈ recalled · L2 · ~6 lines · 12w · Kafka rejected as event bus: ops burden for a team of four
◈◈◈ recalled · L1–L2 · 6 sources · ~420 lines · Aug–Oct · search: OpenSearch, 3 shards, 180 ms p99, BM25-only rejected
◈ recalled · L1 · 6w · superseded · fraud scoring: Stripe Radar → in-house model
```

- **The marker shows how much was drawn on,** by sources or lines read, whichever is larger: `◈` a small single recall, `◈◈` ~50–300 lines or 2–3 sources, `◈◈◈` over ~300 lines or 4+ sources.
- **`~420 lines`** is about how much memory was read for this answer (topic files, session logs, chats; the always-loaded map isn't counted). It's Claude's estimate, hence the `~`.
- **Layers show how deep it dug:** `L0` is the always-loaded map, `L1` a topic file, `L2` a session log, `L3` a raw chat.
- **Scope:** a single memory's age, or for a broad recall how many sources and the time span they cover.
- **The gist:** up to 12 words for one source, 20 for many. The detail is in the answer itself.
- **Flags get their own line,** so a warning is never buried: `superseded` (a newer decision replaced an older one, shown as old → new), `unverified` (no source), or `stale` (a temporary status, like "A/B running", older than 14 days; decisions and facts never go stale by age).

Routine answers, preferences and the rules never get a line, so a recall line means memory earned its keep, and you can spot an outdated memory at a glance.

**On demand**, `/cortex status` prints a dashboard: the memory budget and the rules version, routing quality (topic files missing from the map, how many facts carry sources), how much memory text has actually been pulled into this chat (it measures the size of the tool results, so `Read`, `cat` and `grep` on `memory/` all count, and it resets after compaction), what memory says is current (`now`), your open threads (`next`), ledger totals and anything needing `attention`:

```
◉ CORTEX status  ·  auto  ·  chat a1b2c3d4
──────────────────────────────────────────────────────────────────
activity   ···██··  2 memory writes in 7 days  ·  last 2h ago (engineering/auth.md)
budget     memory ██████░░░░ 1.8k / 3k tok  ·  rules 1.8k tok (current)
routing    map names 12/12 topic files  ·  64% of L1 facts sourced  ·  9/10 logs line-ranged
learning   self-test 7/9 → 8/9 → 9/9 (last 2026-11-02)  ·  next self-test after 3 more changed logs  ·  4 corrections learned
in context 3.5k tok always loaded  ·  pulled in this chat: 4 reads, 612 lines, ~2.4k tok  ·  ~7% of this chat's 61.9k context
now        ▸ Auth moved to short-lived tokens, rollout to staging done
           ▸ Billing webhooks rewritten, retries still flaky
next       ◦ Add idempotency keys to the webhook handler
           ◦ Load-test staging before the Friday cut
ledger     940 lines recorded  ·  200 pending  ·  100 skipped on purpose
this chat  last saved to memory 12m ago  ·  40 transcript lines since
settings   recording auto  ·  hooks ✓  ·  logs on  ·  commit no (memory/ git-ignored)
──────────────────────────────────────────────────────────────────
attention  ⚠ 1 chat with unlogged tails (9f3e21aa)
           ⚠ engineering/deploy.md not updated in 48 days
           ⚠ consolidate: 11 session logs listed in the map (cap 10)
suggest    ▸ /cortex all  (recover unlogged and untracked chats)
```

The values in these samples are illustrative; the layout is real output. Turn the hooks' lines off with `/cortex config logs=off`, or set `CORTEX_QUIET=1` in the environment.

---

## ✨ What that gets you

| | |
|---|---|
| ⚡ **Cold start in seconds** | A new chat begins already knowing the project's decisions, conventions and open questions. |
| 🔎 **Cited recall** | Ask `/cortex recall why did we pick Postgres?` and get an answer with file and line references. |
| ⏪ **Retroactive memory** | `/cortex all` mines the transcripts you already have and merges them into current truth. |
| 🛡️ **Self-audit** | `/cortex audit` checks for duplicated facts, index and file drift, and files over their caps. A cold-start test is available too. |
| 🧾 **Auditable** | Every claim traces to a chat and a line, and every range to the ledger. |
| 🪶 **Cheap** | You pay for a small index on every chat. Everything else is pulled in on demand. |

---

## 🚀 Install

**Requirements:** [Claude Code](https://claude.com/claude-code) and Python 3.9 or newer as `python3`.

```bash
git clone https://github.com/arth17singh/cortex.git
cd cortex
./install.sh
```

That copies the skill to `~/.claude/skills/cortex` and offers to register the hooks (see below). Other options:

```bash
./install.sh --hooks     # install the skill and the hooks without prompting
./install.sh --no-hooks  # skill only
./install.sh --link      # symlink instead: `git pull` here updates the skill everywhere
./install.sh --project   # install into ./.claude/skills and ./.claude/settings.json of this project only
./install.sh --uninstall-hooks   # remove the hooks again
```

An existing skill install is moved to `cortex-backups/cortex.bak-<timestamp>` next to the `skills/` folder, never overwritten.

### 🪝 Hooks

The hooks are what make CORTEX proactive, so you should install them. They are two entries in `settings.json` that run `scripts/cortex_hook.py`:

| Hook | What it does |
|---|---|
| `SessionStart` | Tells Claude this chat's id and transcript, the recording mode, and any unlogged gaps in other chats that need recovering |
| `Stop` | When the ledger falls far behind the transcript, gives Claude a gentle, rate-limited nudge to log what's worth keeping |

`install.sh` merges them into the existing hook arrays without touching your other hooks. It backs up `settings.json` first, is safe to re-run, and re-parses the result to check it. Both hooks do nothing in projects that haven't enabled CORTEX, and they exit quietly if anything goes wrong.

To add them by hand, merge [`hooks/settings-snippet.json`](hooks/settings-snippet.json) into `~/.claude/settings.json`. You can also run `python3 hooks/install_hooks.py <settings.json> <path-to-cortex_hook.py>` yourself, or use `/cortex config hooks=install` from inside Claude Code.

**Manual install:** copy `skills/cortex/` to `~/.claude/skills/cortex/`.

### Updating

```bash
cd cortex && git pull && ./install.sh --no-hooks   # hooks are already registered
```

Then, in each project that already uses CORTEX, run `/cortex upgrade` once. It shows what will change and backs up first. Projects you don't upgrade keep working on their current rules, so you can upgrade each one when it suits you, for example after a deadline.

### Verify

Open Claude Code in any project and run:

```
/cortex help
```

---

## ⚡ Quick start

```text
/cortex start              # record this chat from now on (builds memory/ on first run)
/cortex all                # backfill every past chat that isn't tracked yet
/cortex status             # coverage, settings, size vs. budget, next suggested action
/cortex upgrade            # move an existing project to the current rules and layout
/cortex recall why did we pick Postgres over DynamoDB?
```

On the first run in a project, CORTEX builds `memory/` from your docs and code, copies its rules to `memory/RULES.md`, adds a short import block to `CLAUDE.md`, and asks you:

1. the **recording mode** (`auto` or `manual`),
2. whether to install the **hooks**, and
3. whether `memory/` should be **committed to git** or ignored.

Nothing is installed or changed until you approve it.

---

## 🧰 Commands

| Command | What it does |
|---|---|
| `/cortex help` | Lists the commands, with a short status line |
| `/cortex upgrade` | Moves a project to the current rules and layout (backs up first, refuses while another chat is open) |
| `/cortex start [--from-chat-start]` | Records this chat from now on (or from its first line) |
| `/cortex all [options]` | Backfills untracked past chats. It's safe to re-run. Options: `only <chat>`, `since DATE`, `last N`, `exclude X`, `include-skipped`, `--yes` |
| `/cortex status` | Shows coverage, settings, memory size against budget and warnings |
| `/cortex save [note]` | Runs a full checkpoint, or stores a note even when paused |
| `/cortex pause` / `resume` | Stops or restarts recording for this chat, or with `--project` for the whole project |
| `/cortex exclude <chat>` / `include <chat>` | Permanently leaves a chat out of memory, or puts it back |
| `/cortex forget <topic>` | Finds every mention, shows exact deletions, and keeps the topic from coming back |
| `/cortex recall <question>` | Answers from memory with citations and a confidence level |
| `/cortex audit` | Checks that memory is consistent, not duplicated and within its size caps |
| `/cortex selftest` | Quizzes memory on recent decisions and rejections with a fresh agent, and repairs every miss |
| `/cortex config [key=value]` | Sets `recording`, `commit`, `timezone`, `exclude-default`, `logs`, `rules`, `selftest` or `hooks` |

---

## 📁 What's in this repo

```
cortex/
├── install.sh                      installer (copy / --link / --project, optional hooks)
├── hooks/
│   ├── settings-snippet.json       the two hook entries, ready to merge
│   └── install_hooks.py            safe, idempotent merge/remove into settings.json
├── README.md
├── LICENSE
└── skills/cortex/
    ├── SKILL.md                    the skill: every subcommand's behaviour
    ├── guide/cortex-user-guide.html   illustrated user guide
    ├── reference/                  rules.md (the rules), the CLAUDE.md stub, build steps, ledger and protocol templates
    └── scripts/
        ├── ledger_scan.py          coverage scanner and transcript search
        ├── cortex_status.py        the /cortex status dashboard
        ├── selftest.py             picks recent decisions and rejections to quiz memory on
        ├── extract_transcript.py   readable, redacted transcript extraction
        └── cortex_hook.py          SessionStart / Stop hook
```

---

## 💡 Good to know

- **Transcripts expire.** Claude Code deletes old transcripts after `cleanupPeriodDays` (default 30, set in `~/.claude/settings.json`). That limits how far back `/cortex all` can reach, so run it early. `/cortex status` warns you about chats approaching that limit.
- **`/cortex` is user-invoked only.** The skill sets `disable-model-invocation`, so Claude won't start it on its own.
- **Uninstall:** run `./install.sh --uninstall-hooks`, delete `~/.claude/skills/cortex`, and delete the CORTEX block from your project's `CLAUDE.md` (it's wrapped in `<!-- CORTEX:BEGIN -->` and `<!-- CORTEX:END -->` markers). Your `memory/` folder is yours to keep or delete.

---

## 📄 License

[MIT](LICENSE)
