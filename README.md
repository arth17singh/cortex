# 🧠 CORTEX

**Project memory for Claude Code that maintains itself.**

Every new Claude Code chat starts with amnesia. You re-explain the architecture, repeat your preferences, and rediscover decisions you made last week. CORTEX gives each project a durable, layered memory that Claude reads at the start of a chat and keeps up to date as you work.

It's a single Claude Code skill: a few markdown files and three small Python scripts. It has no dependencies, no server and no database. The memory is plain markdown that you can read, edit and `git diff`.

> 📖 **[Open the user guide](skills/cortex/guide/cortex-user-guide.html)**: a visual walkthrough of the layers, the ledger and every command. Download it and open it in your browser.

---

## ✨ Why you'll like it

| | |
|---|---|
| 🪜 **Layered, so it stays cheap** | Only a small index (~3k tokens) is always loaded. Details are pulled in on demand, so your context window isn't spent on history. |
| 🔁 **Self-maintaining** | Claude checkpoints decisions and facts as the chat runs. A hook flags anything a crashed or abandoned chat left unlogged, so Claude can recover it. |
| ⏪ **Backfills your past chats** | `/cortex all` mines the transcripts you already have and adds them to memory. |
| 🧾 **Honest coverage ledger** | `LEDGER.md` records exactly which lines of which chats are in memory, so nothing is double-counted and nothing is silently missing. |
| 🎛️ **You stay in control** | Pause, resume, exclude a chat, or forget a topic at any time. Anything that reads many chats or changes hooks or settings is shown to you first and waits for your OK. |
| 🔒 **Privacy by default** | Secrets, keys, tokens and anyone's email or phone number are redacted before storage. `.env*` and credential files are never opened. |
| 🔍 **Cited recall** | `/cortex recall <question>` answers from memory with file and line citations and flags what it couldn't verify. |

---

## 🏗️ How it works

Memory lives in a `memory/` folder inside your project, in four layers:

```
L0  CLAUDE.md block + memory/INDEX.md    always loaded: status, a map of every file, how you work
L1  memory/<topic>/*.md                  current truth, kept lean (~150 lines per file)
L2  memory/sessions/*.md                 per-chat history and detail
L3  raw Claude Code transcripts          used only when a step explicitly needs them
```

- **Read path:** Claude starts from L0, follows the index to the right L1 file, and goes down to L2 or L3 only if it needs to.
- **Write path:** durable facts go to L1 with a source tag. Subtle details go to the session log in L2.
- **Hooks:** a `SessionStart` hook tells Claude this chat's id, the recording mode and any unlogged gaps. A `Stop` hook gives Claude a gentle, rate-limited nudge to log what's worth keeping when the ledger falls far behind the transcript. Only Claude marks lines as covered, and only after it has logged them. Both hooks stay silent in projects that haven't enabled CORTEX.

---

## 🚀 Install

**Requirements:** [Claude Code](https://claude.com/claude-code) and `python3`.

```bash
git clone https://github.com/arth17singh/cortex.git
cd cortex
./install.sh
```

That copies the skill to `~/.claude/skills/cortex`. Other options:

```bash
./install.sh --link      # symlink instead: `git pull` here updates the skill everywhere
./install.sh --project   # install into ./.claude/skills of the current project only
```

An existing install is moved aside to `cortex.bak-<timestamp>`, never overwritten.

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
/cortex recall why did we pick Postgres over DynamoDB?
```

On the first run in a project, CORTEX builds `memory/` from your docs and code, adds its block to `CLAUDE.md`, and asks you:

1. the **recording mode** (`auto` or `manual`),
2. whether to install the **hooks**, and
3. whether `memory/` should be **committed to git** or ignored.

Nothing is installed or changed until you approve it.

---

## 🧰 Commands

| Command | What it does |
|---|---|
| `/cortex help` | Lists the commands, with a short status line |
| `/cortex start [--from-chat-start]` | Records this chat from now on (or from its first line) |
| `/cortex all [options]` | Backfills untracked past chats. It's safe to re-run. Options: `only <chat>`, `since DATE`, `last N`, `exclude X`, `include-skipped`, `--yes` |
| `/cortex status` | Shows coverage, settings, memory size against budget and warnings |
| `/cortex save [note]` | Runs a full checkpoint, or stores a note even when paused |
| `/cortex pause` / `resume` | Stops or restarts recording for this chat, or with `--project` for the whole project |
| `/cortex exclude <chat>` / `include <chat>` | Permanently leaves a chat out of memory, or puts it back |
| `/cortex forget <topic>` | Finds every mention, shows exact deletions, and keeps the topic from coming back |
| `/cortex recall <question>` | Answers from memory with citations and a confidence level |
| `/cortex audit` | Checks that memory is consistent, not duplicated and within its size caps |
| `/cortex config [key=value]` | Sets `recording`, `commit`, `timezone`, `exclude-default` or `hooks` |

---

## 📁 What's in this repo

```
cortex/
├── install.sh                      installer (copy / --link / --project)
├── README.md
├── LICENSE
└── skills/cortex/
    ├── SKILL.md                    the skill: every subcommand's behaviour
    ├── guide/cortex-user-guide.html   illustrated user guide
    ├── reference/                  build steps, CLAUDE.md block, ledger and protocol templates
    └── scripts/
        ├── ledger_scan.py          coverage scanner and transcript search
        ├── extract_transcript.py   readable, redacted transcript extraction
        └── cortex_hook.py          SessionStart / Stop hook
```

---

## 💡 Good to know

- **Transcripts expire.** Claude Code deletes old transcripts after `cleanupPeriodDays` (default 30, set in `~/.claude/settings.json`). That limits how far back `/cortex all` can reach, so run it early. `/cortex status` warns you about chats approaching that limit.
- **`/cortex` is user-invoked only.** The skill sets `disable-model-invocation`, so Claude won't start it on its own.
- **Uninstall:** delete `~/.claude/skills/cortex`, remove the `cortex_hook.py` entries from your `settings.json` hooks, and delete the CORTEX block from your project's `CLAUDE.md` (it's wrapped in `<!-- CORTEX:BEGIN -->` and `<!-- CORTEX:END -->` markers). Your `memory/` folder is yours to keep or delete.

---

## 📄 License

[MIT](LICENSE)
