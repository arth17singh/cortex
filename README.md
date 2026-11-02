# 🧠 CORTEX

**A tiered, self-auditing memory architecture for Claude Code.**

Claude Code is stateless between chats. CORTEX adds the missing layer: a hierarchical, provenance-tracked project memory with a coverage ledger, hook-driven capture and an always-loaded part that is bounded by construction. Claude opens every session already oriented, with decisions, rationale, conventions and open threads in context, without paying for them in context window.

It's a single skill: markdown, three stdlib-only Python scripts and two hooks. It has no dependencies, no server, no vector database and no embeddings. The memory is plain markdown, so you can read it, `grep` it and `git diff` it.

> 📖 **[Open the user guide](skills/cortex/guide/cortex-user-guide.html)**: an illustrated walkthrough of the layers, the ledger and every command. Download it and open it in your browser.

---

## 🧬 Architecture

CORTEX is built around five ideas.

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

- **The rules** (`memory/RULES.md`, ~1.7k tokens) are a fixed cost. They ship with the skill, are copied byte-for-byte into each project (no approval dialog, no path dependency), and `/cortex upgrade` refreshes them, project by project.
- **The memory part** has caps: ≤8 dated "Where we are" bullets, ≤10 session logs on the map (older ones move to `sessions/README.md`), ≤6 files per folder (larger folders get their own `_index.md`), ≤40 preference lines. Full to every cap it measures about 3,000 tokens, so it can never grow past that.
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

### 5. Live status
You can see CORTEX working, without it getting in your way.

**At the start of every chat**, one line from the `SessionStart` hook. The bars are a 7-day sparkline of memory writes, so you can see at a glance whether memory is being kept up to date:

```
◉ CORTEX auto  ·  12 topics  ·  31 chats remembered  ·  ▁▃▅··█▂ 7d  ·  last write 2h ago  ·  ⚠ 1 unlogged tail, recovering  ·  /cortex status
```

**After a turn that changed memory**, a pulse naming exactly what was written. It is a before and after snapshot of `memory/`, so it never appears when nothing changed:

```
⟲ CORTEX synced  ·  L1 engineering/auth.md +6 · L2 2026-11-01_a1b2c3d4-auth.md +14  ·  ledger → 388
```

**While Claude works**, one-line `⟦CORTEX⟧` entries for reads, writes, recoveries and checkpoints (written by Claude under the rules in `memory/RULES.md`, and only for actions it actually performed):

```
⟦CORTEX⟧ recall ▸ L1 engineering/auth.md · 118 lines · trust: sourced L1
⟦CORTEX⟧ commit ▸ L2 2026-11-01_a1b2c3d4-auth.md (L341-388) + L1 engineering/auth.md · ledger live → 388
```

**On demand**, `/cortex status` prints a dashboard: the memory budget and the rules version, routing quality (topic files missing from the map, how many facts carry sources), how much memory text has actually been pulled into this chat (it measures the size of the tool results, so `Read`, `cat` and `grep` on `memory/` all count, and it resets after compaction), what memory says is current (`now`), your open threads (`next`), ledger totals and anything needing `attention`:

```
◉ CORTEX status  ·  auto  ·  chat a1b2c3d4
──────────────────────────────────────────────────────────────────
activity   ···██··  2 memory writes in 7 days  ·  last 2h ago (engineering/auth.md)
budget     memory ██████░░░░ 1.8k / 3k tok  ·  rules 1.7k tok (current)
routing    map names 12/12 topic files  ·  64% of L1 facts sourced  ·  9/10 logs line-ranged
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

The values in these samples are illustrative; the layout is real output. Turn the live output off with `/cortex config logs=off`, or set `CORTEX_QUIET=1` to silence the hook alone.

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
| `/cortex config [key=value]` | Sets `recording`, `commit`, `timezone`, `exclude-default`, `logs`, `rules` or `hooks` |

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
