# Memory and project knowledge in coding agents (2023–2026)

Research notes. All web sources were fetched on 2026-11-04. For docs pages with no date, "docs fetched 2026-11-04" is the only date available. Where a source is secondary, a forum thread, a mirror, or a search-result summary that I did not open in full, it is marked as such.

## 1. Aider repo map: tree-sitter symbols, the file/symbol graph, personalised PageRank, the token budget, and evidence it helps

### Takeaway
Aider builds its map fresh on each request, not as stored memory. Tree-sitter `def`/`ref` tags feed a networkx file graph; PageRank, personalised toward the files and identifiers in the chat, ranks it; a binary search then fits the ranked symbols into `--map-tokens` (default 1k). The weighting lives only in the source code; the docs never name PageRank or personalisation. Evidence that it helps is thin. Aider ran no ablation. Its 70.3% correct-file rate on SWE-bench Lite measures the whole stack. The one independent data point (Agent Retrieval Bench, July 2026) found "RepoMap" gave the best context yield within an 8K-token budget, but no retrieval family won overall.

### Cited Findings
**Documented behaviour (docs and blog)**
- The repo map is "a concise map of the whole git repository" listing the most important classes and functions with their types and call signatures. For each file it shows the key symbols and the critical lines of each definition, with `⋮...` elisions. Only the most-referenced identifiers are included — [Aider docs: Repository map](https://aider.chat/docs/repomap.html)
- The docs describe a "graph ranking algorithm" over a graph "where each source file is a node and edges connect files which have dependencies", and say the map focuses on what is "most relevant to the current state of the chat". The docs do not name PageRank, personalisation or tree-sitter — [Aider docs: Repository map](https://aider.chat/docs/repomap.html)
- `--map-tokens` "defaults to 1k tokens". The map size "adjusts dynamically" and "can expand significantly", especially when no files are in the chat. The LLM can ask for specific files, and aider offers to add them — [Aider docs: Repository map](https://aider.chat/docs/repomap.html)
- Blog post (22 Oct 2023): the tree-sitter map "replaces the ctags based map". It shows "full function call signatures and other details straight from the source files". Languages come from the `py-tree-sitter-languages` package, so universal-ctags no longer has to be installed. The post has no benchmark — [Aider blog, 2023-10-22](https://aider.chat/2023/10/22/repomap.html)
- CLI options: `--map-refresh` takes `auto`, `always`, `files` or `manual` (default `auto`). `--map-multiplier-no-files` sets the "Multiplier for map tokens when no files are specified (default: 2)". `--map-tokens 0` disables the map — [Aider options reference](https://aider.chat/docs/config/options.html)

**Implementation (source code `aider/repomap.py`, main branch, fetched 2026-11-04)**
- Tags come from per-language tree-sitter query files (`{lang}-tags.scm`), which mark each tag as `def` or `ref`. Tags are cached on disk (diskcache/SQLite) in `.aider.tags.cache.v{N}`, keyed by filename and invalidated when the file's mtime changes. If SQLite fails, the cache falls back to an in-memory dict — [repomap.py](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py)
- Graph: a `networkx.MultiDiGraph`. For each identifier that is both defined and referenced, there is an edge from each referencing file to each defining file. Edge weight = `mul × sqrt(num_refs)`, where the square root stops high-frequency mentions from dominating. A definition with no references gets a self-edge of weight 0.1 — [repomap.py](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py)
- Multipliers on `mul`: ×10 if the identifier was mentioned in the chat; ×10 if it is snake/kebab/camelCase and at least 8 characters long; ×0.1 if it starts with `_`; ×0.1 if more than 5 files define it; ×50 on edges whose referencing file is in the chat — [repomap.py](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py)
- Personalisation: each chat file, each mentioned file, and each file whose path components match a mentioned identifier gets weight `100/len(fnames)`. The code calls `nx.pagerank(G, weight="weight", personalization=..., dangling=...)`. Each node's rank is then split across its out-edges in proportion to edge weight, giving a score per `(file, identifier)` definition. Files already in the chat are left out of the map — [repomap.py](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py)
- Budget fitting: a binary search over how many ranked tags to render. The first guess is `max_map_tokens // 25` tags, and the search accepts a tree within 15% of the budget (`ok_err = 0.15`). Token counts for long texts are estimated from a sample. With no files in the chat, the budget becomes `min(map_tokens × map_mul_no_files, context_window − 4096)` — [repomap.py](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py)
- Refresh: in `auto` mode a cached map is reused only if the last computation took more than 1.0 s. `files` mode always uses the cache, `always` never does, and `manual` returns the last map — [repomap.py](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py)
- **Discrepancy:** the `RepoMap.__init__` signature defaults `map_mul_no_files=8`, while the CLI option documents a default of 2 — [repomap.py](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py); [Aider options reference](https://aider.chat/docs/config/options.html)

**Evidence of effectiveness**
- SWE-bench Lite write-up (22 May 2024; 26.3% overall): "Aider successfully identified the correct file to edit in 70.3% of the benchmark tasks", measured against the gold patch. The post credits the repo map but reports no ablation without it — [Aider blog, 2024-05-22](https://aider.chat/2024/05/22/swe-bench-lite.html)
- A practitioner pattern page also notes that the SWE-bench write-up "does not isolate its contribution in an ablation" (secondary) — [agentpatterns.ai](https://agentpatterns.ai/context-engineering/repository-map-pattern/)
- Agent Retrieval Bench (Qin & Xie, 27 Jul 2026, arXiv preprint): 427 samples across 25 repos, at file level. "No single retrieval family dominates". Qwen3-Embedding-4B has the best MRR and Qwen3-Embedding-8B the best Recall@20. "RepoMap has the best budgeted context yield at 8K tokens", though task-level winners vary a lot. Logged agent trajectories miss every gold file on 27–35% of samples. The abstract gives no exact numbers, and I could not confirm that its "RepoMap" is aider's implementation — [arXiv 2607.24882](https://arxiv.org/abs/2607.24882)

### Inferences
- The repo map is derived data that is recomputed and invalidated by mtime. It cannot go stale the way a stored note can, which makes it a useful contrast with "memory".
- The personalisation design is "rank code by its structural closeness to what's in the chat now". The same idea carries over to ranking memory records by the files and identifiers in the current prompt.
- For a Python-stdlib-only build: power-iteration PageRank with a personalisation vector takes about 30 lines; `ast` can extract defs and refs for Python; tokens can be estimated as chars/4 for the binary search; an mtime-keyed JSON cache replaces diskcache. Multi-language def/ref extraction needs tree-sitter, which is not stdlib, or regex heuristics.

### Gaps
- No controlled ablation of the repo map (or of personalised PageRank against BM25 or embeddings) by aider or anyone else was found. Agent Retrieval Bench's per-method numbers were not available from the abstract.
- The effective default for `--map-tokens` in current aider may be model-dependent. The options page snippet did not state a number; the "1k" comes from the repo-map docs page.

## 2. Claude Code: memory files, hooks, compaction, transcript storage (official docs)

### Takeaway
Claude Code layers several kinds of instruction memory: CLAUDE.md files (managed, user, project and local scopes; ancestor directories loaded at launch, subdirectories on demand; `@imports` up to 4 hops), path-scoped `.claude/rules/`, and an "auto memory" directory that Claude writes itself (`MEMORY.md` index, of which the first 200 lines or 25KB load). Hooks can inject `additionalContext` (capped at 10,000 characters) at SessionStart, UserPromptSubmit, PreToolUse and PostToolUse. They can block or rewrite tool calls, keep Claude working at Stop, and block, but not steer, compaction. Compaction re-injects CLAUDE.md and auto memory from disk, but context that hooks injected is only summarised. Transcripts are plaintext JSONL under `~/.claude/projects/` and are deleted after `cleanupPeriodDays` (default 30). Auto memory is exempt from that sweep.

### Cited Findings
**CLAUDE.md hierarchy and loading** ([memory docs](https://code.claude.com/docs/en/memory), docs fetched 2026-11-04)
- Scopes, in load order from broadest to most specific:
  - Managed policy: `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS), `/etc/claude-code/CLAUDE.md` (Linux/WSL), `C:\Program Files\ClaudeCode\CLAUDE.md` (Windows)
  - User: `~/.claude/CLAUDE.md`
  - Project: `./CLAUDE.md` or `./.claude/CLAUDE.md`
  - Local: `./CLAUDE.local.md` (gitignored)
  — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Files in the cwd and every ancestor directory load at launch and are "concatenated into context rather than overriding each other", ordered from the root down. `CLAUDE.local.md` is appended after `CLAUDE.md` at each level. Subdirectory CLAUDE.md files load "once Claude reads, writes, or edits another file in that subdirectory", and a Bash `cat` or `head` counts as a read — [memory docs](https://code.claude.com/docs/en/memory)
- `@path` imports resolve relative to the importing file and can recurse "with a maximum depth of four hops". Imports in a project file that point outside the working directory trigger a one-time approval dialog. Imports inside code spans are not parsed. Block-level HTML comments are stripped before injection. Imports "don't reduce its context cost" — [memory docs](https://code.claude.com/docs/en/memory)
- Size guidance: "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." A file over 4 MiB is skipped. On-demand files (subdirectory CLAUDE.md, path-scoped rules) are truncated above a per-file limit of 40,000 characters on a 200K window (150,000–200,000 on 1M windows), followed by a note telling Claude to read the rest — [memory docs](https://code.claude.com/docs/en/memory)
- `.claude/rules/*.md` files are discovered recursively. Rules without `paths` frontmatter load at launch. Rules with `paths:` globs load when Claude uses Read, Write or Edit on a matching file. `paths` is the only frontmatter field read — [memory docs](https://code.claude.com/docs/en/memory)
- "CLAUDE.md content is delivered as a user message after the system prompt, not as part of the system prompt itself… there's no guarantee of strict compliance." If two instructions contradict each other, "Claude may pick one arbitrarily". To block an action whatever Claude decides, the docs say to use a PreToolUse hook — [memory docs](https://code.claude.com/docs/en/memory)
- `/doctor prompt-audit` (v2.1.283+) checks instruction files for "instructions written for older models, references to files or commands that don't exist, and files that contradict each other", and proposes edits. This is a documented staleness check for instruction memory — [memory docs](https://code.claude.com/docs/en/memory)
- AGENTS.md (v2.1.277+) is read when no CLAUDE.md or CLAUDE.local.md exists in the cwd or above. A "Project instructions" setting can make Claude read both — [memory docs](https://code.claude.com/docs/en/memory)

**Auto memory**
- Claude saves four `type`s of note: `user`, `feedback`, `project` and `reference`. "Claude skips anything it can derive from the codebase, such as architecture, file paths, or debugging fixes. It also skips anything your CLAUDE.md files already say." — [memory docs](https://code.claude.com/docs/en/memory)
- Storage is `~/.claude/projects/<project>/memory/`, with the project derived from the git repo, so worktrees share one directory. It holds a `MEMORY.md` index ("one line per memory, loaded into every session") plus one topic file per memory. Topic files are read on demand with the normal file tools. Auto memory is machine-local and is not loaded into subagents, except forks — [memory docs](https://code.claude.com/docs/en/memory)
- "The first 200 lines of `MEMORY.md`, or the first 25KB, whichever comes first, are loaded at the start of every conversation." Near a limit, Claude Code reminds Claude to shorten the index and "merge or drop stale entries". Over a limit, the write succeeds but returns an error telling Claude to rewrite the index, "because everything past the limit is dropped on the next load" — [memory docs](https://code.claude.com/docs/en/memory)
- When Claude writes a memory file with YAML frontmatter, Claude Code records a `modified` ISO-8601 timestamp "so … how current the fact is" is visible — [memory docs](https://code.claude.com/docs/en/memory)
- Auto memory is on by default in local sessions. Sessions in self-hosted environments, outside Claude Tag sessions, start with it off. It can be toggled with `autoMemoryEnabled` (user or project settings) or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, and relocated with `autoMemoryDirectory` — [memory docs](https://code.claude.com/docs/en/memory)

**Hooks** ([hooks reference](https://code.claude.com/docs/en/hooks.md), docs fetched 2026-11-04)
- Events and decision control:
  - **SessionStart**: matchers `startup`, `resume`, `clear`, `compact`, `fork`. Context only, via `additionalContext` or plain stdout; cannot block. Only `command` and `mcp_tool` hook types are supported.
  - **UserPromptSubmit**: `decision: "block"` with a `reason`, plus `additionalContext`. Plain stdout is added as context. The prompt cannot be rewritten.
  - **PreToolUse**: `permissionDecision` (`allow`/`deny`/`ask`/`defer`), `updatedInput` (rewrites tool arguments), `additionalContext`.
  - **PostToolUse**: `decision: "block"`, `updatedToolOutput`, `additionalContext`.
  - **Stop**: `decision: "block"` keeps Claude working.
  - **PreCompact**: blocks only.
  - **PostCompact** and **SessionEnd**: no decision control.
  — [hooks reference](https://code.claude.com/docs/en/hooks.md)
- Exit codes: 0 means success, and stdout is parsed as JSON when it is a single object. 2 is a "blocking error" on events that support blocking, with stderr as the reason. Any other code is a non-blocking error. `additionalContext`, `systemMessage` and `initialUserMessage` strings are "capped at 10,000 characters"; longer output is saved to a file and Claude receives the path plus a 2,000-character preview — [hooks reference](https://code.claude.com/docs/en/hooks.md)
- UserPromptSubmit injections are delivered "as a system reminder that starts with the hook's name". "Neither channel produces a visible transcript entry." The default timeout is 30 s for command, http and mcp_tool hooks. On timeout the output, "including any `additionalContext`, is discarded" and the prompt proceeds without it. The hook also fires on scheduled tasks, on background-subagent reports and on cross-session messages — [hooks reference](https://code.claude.com/docs/en/hooks.md)
- Stop input includes `stop_hook_active` and `last_assistant_message`. The docs advise using the latter because "the transcript file isn't guaranteed to include the final message at Stop time". After 8 consecutive Stop-hook continuations Claude Code overrides the block (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`). `transcript_path` "is written asynchronously and may lag the current turn" — [hooks reference](https://code.claude.com/docs/en/hooks.md)
- PreCompact fires with matcher `manual` (`/compact`) or `auto` (auto-compact and idle compaction). It can block with exit 2 or `"decision": "block"`. Its input carries `trigger` and `custom_instructions` (the user's `/compact` text, or `null` for auto). Claude Code discards its `systemMessage` and `continue` fields. The docs describe no field for adding instructions to the summary. PostCompact receives `compact_summary` and "can't affect the compaction result" — [hooks reference](https://code.claude.com/docs/en/hooks.md)
- Hook types: `command`, `http`, `mcp_tool`, `prompt` (a single-turn Claude decision) and `agent` (a subagent with Read/Grep/Glob, experimental). Default timeouts: 600 s for command/http/mcp_tool, 30 s for prompt, 60 s for agent. SessionEnd hooks share a 1.5 s budget, which can be raised to 60 s. `"async": true` runs a hook in the background with no timeout enforced; `asyncRewake` wakes Claude on exit 2 — [hooks reference](https://code.claude.com/docs/en/hooks.md)

**Compaction** ([context-window page](https://code.claude.com/docs/en/context-window.md))
- What survives compaction:
  - Project-root CLAUDE.md, unscoped rules and auto memory: "Re-injected from disk".
  - Path-scoped rules and nested CLAUDE.md: reloaded on demand (they were in message history, so compaction summarises them away).
  - Files Claude read or edited: up to five are re-read, most recently modified first. A file over 5,000 tokens comes back as a path reference only.
  - Invoked skill bodies: re-injected with caps of 5,000 tokens per skill and 25,000 tokens in total.
  - "Context that hooks added earlier": "Summarized with the rest of the conversation".
  - SessionStart hooks matching `compact`: run again, and their output is added to the compacted context.
  — [context-window page](https://code.claude.com/docs/en/context-window.md)
- Users can steer compaction with `/compact <focus>`, summarise part of a conversation with `/rewind`, set the threshold with `/autocompact`, and enable idle compaction — [context-window page](https://code.claude.com/docs/en/context-window.md)
- The memory docs add: "Project-root CLAUDE.md survives compaction: after `/compact`, Claude re-reads it from disk and re-injects it" — [memory docs](https://code.claude.com/docs/en/memory)

**Transcripts and retention** ([.claude directory page](https://code.claude.com/docs/en/claude-directory.md); [settings reference](https://code.claude.com/docs/en/settings-reference.md))
- `projects/<project>/<session>.jsonl` holds the "Conversation transcript: messages, tool calls, and tool results, plus the system prompt, tool definitions, and parameters of the requests". Subagent transcripts live in `<session>/subagents/` and large tool outputs in `<session>/tool-results/`. `file-history/` keeps snapshots for the 100 most recent checkpoints — [.claude directory](https://code.claude.com/docs/en/claude-directory.md)
- `cleanupPeriodDays`: "Default: `30`", a whole number with minimum 1. "Setting `0` fails validation, so pick a large value such as `3650`". The deletion runs as a background sweep after a session starts and "deletes transcripts without showing a message" — [settings reference](https://code.claude.com/docs/en/settings-reference.md)
- The sweep does not delete auto-memory files. The memory directory is removed only if it has been empty for the whole retention period. Before v2.1.228 the sweep could delete folders inside the memory directory — [.claude directory](https://code.claude.com/docs/en/claude-directory.md)
- "Transcripts and history are not encrypted at rest… If a tool reads a `.env` file or a command prints a credential, that value is written to `projects/<project>/<session>.jsonl`." — [.claude directory](https://code.claude.com/docs/en/claude-directory.md)

### Inferences
- Context injected by hooks gets summarised at compaction. A hook-based memory system should therefore re-inject its critical state through a SessionStart hook with the `compact` matcher, or keep it in files that are re-injected from disk (CLAUDE.md, imports, MEMORY.md). PreCompact cannot steer the summary.
- Anthropic's own auto-memory policy (skip anything derivable from the code, timestamp each write, keep a bounded index with on-demand topic files) reads as a staleness-avoidance design: don't store what the code already says.
- With the default 30-day retention, transcript-based backfill must run within 30 days, or the user must raise `cleanupPeriodDays`.
- `prompt` and `agent` hook types call a model synchronously, with default timeouts of 30 s and 60 s. Under a "small-model calls only in background jobs" constraint, model work belongs in a detached process started from a command hook (or an `async: true` hook), not in these hook types.

### Gaps
- I did not find the release version or date when auto memory first shipped, or any official measurement of its effectiveness.
- Claude Code version numbers in these docs (v2.1.2xx–2.1.3xx) are current as of the 2026-11-04 fetch. Behaviour may differ on older installs.

## 3. Cursor, Windsurf, Cline, GitHub Copilot, OpenAI Codex, Devin: what each stores, when it writes, how it retrieves, known problems

### Takeaway
Every product separates two things. One is human-authored, version-controlled instruction files (rules, AGENTS.md, copilot-instructions), which load always or by glob. The other is agent-written "memories", which are machine-local or server-side and recalled by relevance or recency. The vendors increasingly demote the second to a "recall layer". Cursor removed Memories in 2.1 (Nov 2025). Devin deprecated Knowledge in favour of Skills. Windsurf and Codex tell users to put durable rules in rules files or AGENTS.md. GitHub Copilot Memory is the only system found that links memories to code: each memory carries file:line citations that are re-verified against the current branch before use, with expiry and voting. Copilot is also the only vendor that published A/B gains.

### Cited Findings
**Cursor**
- Rules: Project Rules are `.mdc` files in `.cursor/rules` with frontmatter `description`, `globs` and `alwaysApply`. There are four modes: Always Apply, Apply Intelligently (agent decides from the description), Apply to Specific Files (globs) and Apply Manually (@-mention). There are also User Rules, Team Rules and AGENTS.md. Guidance: "Keep rules under 500 lines". Precedence is Team → Project → User. A plain `.md` file in `.cursor/rules` is ignored — [Cursor docs: Rules](https://cursor.com/docs/context/rules)
- Memories launched as a beta in Cursor 1.0, enabled from Settings → Rules, and stored per project per user. This is from a search summary of the changelog pages; the "per project per user" wording came from a regional version — [Cursor 1.0 changelog](https://cursor.com/changelog/1-0). 1.2 reportedly made Memories GA and added "user approvals for background-generated memories". This comes from an unofficial mirror and a news summary, not cursor.com — [cursor-fan mirror](https://cursor-fan.pages.dev/blog/2025/07/03/cursor-1-2-agent-planning-better-context-faster-tab); [AlternativeTo](https://alternativeto.net/news/2025/7/cursor-1-2-adds-agent-generated-to-dos-queued-tasks-and-merge-conflict-help)
- Removal: in forum threads (late 2025 to 2026), staff said Memories were removed in the 2.1 line. One reply says "starting from version 2.1.17", others say "2.1.x", so the two are inconsistent. Staff suggested "Export memories" to an `.mdc` file to move into Rules; one user said the option was missing on 2.1.34. In a 2.2.44 thread staff said memories "still work, just without a UI", and a user reported the agent still holding 32 memories. These details come from search-result summaries of the threads — [forum: Are my memories gone?](https://forum.cursor.com/t/are-my-memories-gone/144057); [forum: Memories not showing](https://forum.cursor.com/t/memories-not-showing/143820); [forum: Can't clear memories](https://forum.cursor.com/t/cant-clear-memories/148254)
- In the "Custom modes and memories gone in 2.1" thread (23 Nov 2025), staff addressed only Custom Modes ("intentionally removed in Cursor 2.1") and gave no reason for removing Memories. The user who opened the thread called Cursor "unusable" without them — [forum thread](https://forum.cursor.com/t/custom-modes-and-memories-gone-in-2-1/143744)

**Windsurf (Cascade; docs now hosted by Cognition/Devin)**
- During a conversation, "Cascade can automatically generate and store memories if it encounters context that it believes is useful to remember". Users can also ask it to "create a memory of …". Memories are tied to their workspace and stored locally in `~/.codeium/windsurf/memories/`. They are retrieved "when it believes that they are relevant", are not available in other workspaces, are "not committed to your repository", and "do NOT consume credits". This is from the Spanish docs page, because the English URL redirects to a Devin Desktop page without this content — [Windsurf docs (es): Memories & Rules](https://docs.windsurf.com/es/windsurf/cascade/memories.md)
- The same page recommends: for knowledge Cascade should reuse reliably, "write it as a Rule or add it to `AGENTS.md`… rather than relying on auto-generated Memories". Rules files: global `~/.codeium/windsurf/memories/global_rules.md` (always on, 6,000 characters) and workspace `.windsurf/rules/*.md` (12,000 characters each, with activation modes). AGENTS.md at the root is always on; in a subdirectory it acts as an auto-glob for that directory — [Windsurf docs (es)](https://docs.windsurf.com/es/windsurf/cascade/memories.md); [JetBrains plugin page](https://docs.devin.ai/windsurf/plugins/cascade/memories.md)
- Devin Desktop (successor UI) uses `.devin/rules/*.md` with `trigger` set to `always_on`, `glob`, `model_decision` or `manual`. `AGENTS.md`, `AGENTS.local.md` and `AGENT.md` are read as always-on rules, and legacy `.windsurf` rules are imported — [Devin Desktop customizations](https://docs.devin.ai/desktop/cascade/memories)
- Known problem: Rehberger (2025) showed that Cascade's `create_memory` tool "is automatically invoked" with no human approval, so an indirect prompt injection (from a GitHub issue, source code or a website) can plant persistent instructions in memory ("SpAIware"). He said Windsurf had not responded since his end-of-May report — [Embrace The Red](https://embracethered.com/blog/posts/2025/windsurf-spaiware-exploit-persistent-prompt-injection)

**Cline Memory Bank**
- Memory Bank is a methodology, not a built-in feature: "a documentation methodology" installed as a Cline Rules file (e.g. `.clinerules/memory-bank.md`) or as custom instructions. It "works with any AI that can read docs". The files live in `memory-bank/`: `projectbrief.md`, `productContext.md`, `activeContext.md`, `systemPatterns.md`, `techContext.md` and `progress.md`, in a hierarchy — [Cline docs](https://docs.cline.bot/prompting/cline-memory-bank)
- Read policy: "I MUST read ALL memory bank files at the start of EVERY task". Updates happen after significant changes, when new patterns are discovered, or on the user command "update memory bank", which triggers "a full documentation review". The docs note that `activeContext.md` changes most often. When the context fills, the workflow is to update the memory bank, start a new chat and say "follow your custom instructions" — [Cline docs](https://docs.cline.bot/prompting/cline-memory-bank)

**GitHub Copilot: custom instructions**
- Repository-wide instructions go in `.github/copilot-instructions.md`. Path-specific instructions go in `.github/instructions/**/NAME.instructions.md`, with frontmatter `applyTo` (globs) and optional `excludeAgent` (`"code-review"` or `"cloud-agent"`). AGENTS.md files can sit anywhere, and "the nearest `AGENTS.md`… will take precedence". A single root `CLAUDE.md` or `GEMINI.md` is an alternative. "Personal instructions take the highest priority." Code review reads instructions "from the head branch" — [GitHub docs: repository instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)

**GitHub Copilot Memory (agentic memory)**
- Engineering blog (Tiferet Gazit, 15 Jan 2026):
  - Format: a memory has a subject, a fact, citations to code locations (e.g. `src/client/sdk/constants.ts:12`) and a reason. Agents write memories with a `store_memory` tool call when something is "likely to have actionable implications for future tasks".
  - Retrieval: "the most recent memories for the target repository" are put in the prompt at session start. Search and weighted prioritisation are listed as future work.
  - Verification: before applying a memory, the agent checks the citations against the current branch. If the code contradicts it or a citation is invalid, the agent "is encouraged to store a corrected version". If it is validated, the agent re-stores it to refresh the timestamp. Verification is "a small number of simple read operations" with no significant added latency.
  — [GitHub blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- Scope and results from the same post:
  - Memories can only be created by contributors with write permission, and only used on the same repository by users with read permission.
  - Adversarial test: memories planted to contradict the code were caught and corrected ("self-healing"). No numbers are given.
  - Code-review offline eval: "3% increase in precision and 4% increase in recall".
  - Coding-agent A/B: PR merge rate 90% with memory vs 83% without. That is 7 percentage points, about 8.4% relative.
  - Code-review A/B: positive feedback 77% vs 75%. Both A/Bs are reported at "p-value <0.00001".
  — [GitHub blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- **Expiry, three versions:**
  - (a) The blog (15 Jan 2026) describes no fixed window, only refresh on validation — [blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
  - (b) The changelog (15 Jan 2026, public preview) says memories are "Automatically expired after 28 days to prevent stale information", are "validated against the current codebase before use", are repository-specific, are shared across the coding agent, code review and CLI, and can be reviewed under Repository Settings > Copilot > Memory — [GitHub changelog](https://github.blog/changelog/2026-01-15-agentic-memory-for-github-copilot-is-in-public-preview/)
  - (c) The current docs (undated, fetched 2026-11-04) give a 90-day default from creation. Upvoting resets the period; "Retrieval alone does not". Orgs can set 7–180 days. A hidden voting system upvotes validated memories and downvotes wrong or outdated ones; memories downvoted past a threshold stop being used — [GitHub docs: Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- Current docs, other points:
  - Two kinds of memory: repository facts and user-level preferences.
  - Copilot "does not treat a memory as permanently true once it has been stored".
  - Limitations: memories are not pooled across repos and forks don't inherit them; memories containing detected secrets or "Recognized model-control tokens" are rejected; "Repository facts can come from closed, unmerged pull requests, and Copilot may not catch every outdated fact"; memories count toward tokens and credits; the SDK has no list, edit or delete APIs.
  — [GitHub docs: Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- Secondary coverage dates an earlier start (19 Dec 2025, Pro/Pro+). This is from a search summary; I did not open the pages — [joshuaberkowitz.us](https://joshuaberkowitz.us/blog/news-1/ai-gets-personal-github-unveils-copilot-memory-for-smarter-coding-2138); [codelabsacademy](https://codelabsacademy.com/en/news/github-copilot-memory-model-choices/)

**OpenAI Codex**
- AGENTS.md:
  - Global: `~/.codex` (or `CODEX_HOME`) checks `AGENTS.override.md`, then `AGENTS.md`.
  - Project: Codex walks from the root ("typically the Git root") down to the cwd. In each directory it checks `AGENTS.override.md`, then `AGENTS.md`, then `project_doc_fallback_filenames`, and takes at most one file per directory.
  - Files are concatenated root-down, so closer files come later. Codex stops adding files at `project_doc_max_bytes` (default 32 KiB).
  - The chain is built "once per run", with no cache.
  — [Codex docs: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) (redirected from developers.openai.com/codex/guides/agents-md)
- Codex Memories:
  - "Generated memory files from eligible prior chats", written in the background once a chat "has been idle long enough", in `$CODEX_HOME/memories_v2/` (or a legacy `memories/`). Secrets are redacted.
  - Config: `memories.generate_memories` and `memories.use_memories` are separate switches. `memories.disable_on_external_context` keeps chats that used MCP, web search or tool search out of generation. Separate `extract_model` and `consolidation_model` settings exist.
  - Local memories are "off by default". Hand edits are not the supported control. The docs say "Treat memories as a helpful recall layer, not as the only source for rules that must always apply."
  — [Codex docs: Memories](https://learn.chatgpt.com/docs/customization/memories?surface=app)
- A secondary blog says Memories arrived with an "April 16" (2026) update (unverified) — [codex.danielvaughan.com](https://codex.danielvaughan.com/2026/05/02/codex-cli-daily-driver-setup-may-2026-opinionated-config/)

**Devin Knowledge**
- A knowledge item has a "trigger description" and "a handful of sentences" of content, plus an optional macro. Devin "will retrieve a Knowledge item when its current work is related to the specified triggers", meaning "when relevant, not all at once or all at the beginning". Devin suggests items from chat feedback for the user to edit or dismiss. Items can be pinned to one repo or all repos. Tip: keep content current "since Devin reads all of it". Status: "deprecated and will be removed in a future update", with items migrating to Skills — [Devin docs: Knowledge](https://docs.devin.ai/product-guides/knowledge)

### Inferences
- The consensus architecture is a small, always-loaded, human-owned rules layer plus an optional, agent-written recall layer that is filtered by relevance or recency. Vendors say the recall layer must not carry must-follow rules (Windsurf, Codex, Copilot), and some have dropped it (Cursor, Devin).
- Copilot is the only vendor that ties memories to code coordinates and re-verifies them at use time. It is also the only one with published effect sizes: modest, single-digit points.
- Copilot's expiry moved from 28 days in the Jan 2026 preview to a 90-day default with voting in the current docs. This suggests the TTL was retuned after the preview. The docs page carries no date, so when it changed is unknown.

### Gaps
- No official explanation was found for why Cursor removed Memories, or how its background memory generation worked (model, triggers). The 1.2 GA and approval details come from unofficial sources.
- Windsurf's retrieval method ("when it believes they are relevant") is undocumented.
- No published effectiveness numbers were found for Cursor Memories, Windsurf memories, Cline Memory Bank, Codex Memories or Devin Knowledge.
- The exact Cursor 1.0 release date and the exact date of the Rehberger Windsurf post were not confirmed from the fetched pages.

## 4. Research on agents learning from past episodes (Reflexion, ExpeL, AWM, SWE-agent, 2025–2026 SWE memory papers)

### Takeaway
Memory from past episodes helps when it is distilled and retrieved selectively. Reported gains on SWE tasks are modest: about 2–7 points on SWE-bench Verified, and about 3–5 points of file-localisation Acc@5. Dumping all memories into context can hurt. CTIM-Rover's ExpeL-style memory made AutoCodeRover worse (42% → 40% full, 31% memory-only, n = 45), which the authors blame on distracting, unfiltered items. Commit history works as code-grounded episodic memory (RepoMem), but helps less, or hurts, in repos with sparse history.

### Cited Findings
- **Reflexion** (Shinn et al., Mar 2023): agents keep "reflective text in an episodic memory buffer to induce better decision-making in subsequent trials". It reports "91% pass@1 accuracy on the HumanEval coding benchmark", above GPT-4's 80%. The memory serves retries of the same task, not cross-session learning (my reading of "subsequent trials") — [arXiv 2303.11366](https://arxiv.org/abs/2303.11366)
- **ExpeL** (Zhao et al., Aug 2023, AAAI-24): learns "without requiring parametric updates" — [arXiv 2308.10144](https://arxiv.org/abs/2308.10144). Method details from the full paper:
  - Gathering: Reflexion-style retries on training tasks (up to 3).
  - Insights: an LLM edits a growing insight list with ADD/EDIT/UPVOTE/DOWNVOTE. Importance starts at 2, and an insight is removed when it reaches 0.
  - Retrieval: successful trajectories are retrieved by kNN (all-mpnet-base-v2 + Faiss; k = 6/2/2/3).
  — [ExpeL full text](https://arxiv.org/html/2308.10144v3)
- ExpeL results (success rate): HotpotQA, ReAct 28.0 → ExpeL 39.0; ALFWorld, 40.0 → 59.0; FEVER transfer, 63 → 70. On ALFWorld with Reflexion rounds, ExpeL+Reflexion reaches 64.2 at R3 vs 54.4 for ReAct+Reflexion. The paper reports HotpotQA as both 40% and 39.0% in different places — [ExpeL full text](https://arxiv.org/html/2308.10144v3)
- **Agent Workflow Memory** (Wang, Mao, Fried, Neubig, Sep 2024): induces reusable "workflows" from past trajectories, either offline (from training examples) or online (from test queries). It "substantially improves the baseline results by 24.6% and 51.1% relative success rate" on Mind2Web and WebArena. Online AWM surpasses baselines by "8.9 to 14.0 absolute points" as the train–test gap widens, and needs fewer steps on WebArena. These are web-agent tasks, not SWE — [arXiv 2409.07429](https://arxiv.org/abs/2409.07429)
- **SWE-agent** (Yang et al., May 2024): an agent–computer interface. It reports 12.5% pass@1 on SWE-bench and 87.7% on HumanEvalFix. The abstract describes no cross-episode memory — [arXiv 2405.15793](https://arxiv.org/abs/2405.15793)
- **CTIM-Rover** (Lindenbauer, Groh, Schütze, May 2025, REALM '25): AutoCodeRover plus a general and repository-level Cross-Task-Instance Memory based on ExpeL. It "does not outperform AutoCodeRover in any configuration" — [arXiv 2505.23422](https://arxiv.org/abs/2505.23422)
- CTIM-Rover numbers (45 SWE-bench Verified instances):
  - Resolution: ACR 42%, CTIM-Rover 40%, CTIM-only 31%, general-only 36%, repo-only 31%, exemplar-only 40%.
  - Median context at the patch step: 10,027 tokens for ACR vs 17,807 for CTIM-Rover.
  - Causes: "distracting CTIM items or exemplar trajectories". For example, a repo-level item containing "clean" pushed the agent to the wrong function on django-13933. All items are given at the start with no relevance filter.
  - Recommendations (untested): embedding retrieval and a relevant subset at each turn.
  — [CTIM-Rover full text](https://arxiv.org/html/2505.23422v1)
- **SWE-Exp** (Chen et al., Jul 2025; v2 Feb 2026): a "multi-faceted experience bank that captures both successful and failed repair attempts", from "high-level problem comprehension to specific code changes". v2 reports 73.0% Pass@1 on SWE-bench Verified with Claude 4 Sonnet; v1 reported 41.6% with DeepSeek-V3-0324 (per search summary). The abstract gives no baseline figures — [arXiv 2507.23361](https://arxiv.org/abs/2507.23361)
- **ReasoningBank** (Ouyang et al., Google, Sep 2025, ICLR 2026) — [full text](https://arxiv.org/html/2509.25140v2):
  - Memory items: title, one-sentence description and content, at most 3 per trajectory. Success or failure is judged by an LLM.
  - Retrieval: top-k by cosine similarity (gemini-embedding-001; default k = 1), added to the system prompt.
  - SWE-Bench-Verified: Gemini-2.5-flash 34.2 → 38.8 (average steps 30.3 → 27.5); Gemini-2.5-pro 54.0 → 57.4 (steps 21.1 → 19.8). The Synapse baseline scored 35.4 and 53.4.
  - Adding failure trajectories helped ReasoningBank (46.5 → 49.7) but hurt AWM (44.4 → 42.2) on WebArena-Shopping.
- **RepoMem: "Improving Code Localization with Repository Memory"** (Wang et al., Oct 2025, ICLR 2026). Commit history serves as memory. Details are in Section 5. File-level Acc@5 on SWE-bench Verified went from 71.6 to 76.5 over LocAgent — [arXiv 2510.01003](https://arxiv.org/abs/2510.01003); [full text](https://arxiv.org/html/2510.01003v2)
- **MemGovern** (Jan 2026): turns raw GitHub issue and PR data into 135K "agent-friendly experience cards" with an "agentic experience search". It reports improved "resolution rates on the SWE-bench Verified by 4.65%", without saying whether this is absolute or relative — [arXiv 2601.06789](https://arxiv.org/abs/2601.06789)
- **Structurally Aligned Subtask-Level Memory** (Shen et al., Feb 2026; listed as an ICML 2026 poster): instance-level memory suffers a "granularity mismatch" causing "misguided retrieval when tasks with similar surface descriptions require distinct reasoning logic". Subtask-aligned memory gives +4.7 pp mean Pass@1 over vanilla agents on SWE-bench Verified, and +6.8 pp on Gemini 2.5 Pro — [arXiv 2602.21611](https://arxiv.org/abs/2602.21611); [ICML listing](https://icml.cc/virtual/2026/poster/66605)

### Inferences
- The papers agree on three things. Distil before storing (insights, workflows, strategies, experience cards). Retrieve a few relevant items instead of injecting everything (ReasoningBank uses k = 1; CTIM-Rover's failure came from unfiltered injection). Align memory granularity with the task step.
- Learning from failures is fragile: it helped ReasoningBank and hurt AWM. A "rejected option" or "lesson" store needs its own evaluation.
- All distillation steps (ExpeL insights, AWM workflows, ReasoningBank items, SWE-Exp experiences) need a model call. In a hook-driven system that call would run in a background job after Stop; only retrieval needs to be synchronous.
- Most gains were measured on SWE-bench-style single-issue tasks with memory built from other instances. None of these papers measures a single developer's multi-session project memory, the closest real-world analogue to the CORTEX use case.

### Gaps
- I did not verify SWE-Exp's baselines or base framework. The v1 41.6% figure comes from a search summary.
- I did not find SWE-Bench-CL or other continual-learning SWE benchmarks in the fetched sources, and did not check Agent KB (2507.06229).
- No paper was found that evaluates cross-session memory for a coding assistant on a real developer's own project history with blind questions.

## 5. Code-aware memory: linking notes to files, symbols and commits; detecting staleness when code changes; using import/call graphs for impact questions

### Takeaway
The production reference design is GitHub Copilot Memory: file:line citations, re-checked against the current branch at use time, plus self-correction, a TTL and voting. Pre-LLM documentation tools solved the same problem earlier. Swimm's "code-coupled" docs are verified on every change and auto-synced. Tan, Wagner and Treude's checker flags code-element names in docs that no longer exist anywhere in the source. Open-source agent-memory tools (2025–2026) converge on content-hash or AST-hash anchors that are re-resolved at recall, with git hooks as a secondary trigger, but none has independent evaluation. For "what does this affect" questions, research systems build def/ref and import/call graphs (RepoGraph, LocAgent) or mine commit history (RepoMem). Reported SWE-bench gains are small (+2–2.7 points on SWE-bench Lite for RepoGraph). LocAgent reports 92.7% file-level localisation.

### Cited Findings
**Citations plus verification at use**
- Copilot memories store citations like `src/client/sdk/constants.ts:12`. Before use, the agent verifies them against the current branch. A memory that is contradicted or has an invalid citation should be re-stored in corrected form; a validated one is re-stored to refresh its timestamp. In adversarial tests, planted false memories were corrected ("self-healing") — [GitHub blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- Copilot docs: validated memories are upvoted and wrong or outdated ones downvoted. Expiry is 90 days by default and resets on upvote. Repository facts "can come from closed, unmerged pull requests, and Copilot may not catch every outdated fact" — [GitHub docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)

**Avoiding staleness by not storing derivable facts**
- Claude Code auto memory skips "anything it can derive from the codebase, such as architecture, file paths, or debugging fixes", and timestamps writes with a `modified` field. `/doctor prompt-audit` flags "references to files or commands that don't exist" — [Claude Code memory docs](https://code.claude.com/docs/en/memory)

**Code-coupled documentation (pre-LLM)**
- Swimm: "When changes are made to your code, Swimm verifies all code-coupled elements within your Swimm documents to match the latest source file updates". Its patented Auto-sync updates snippets, tokens and paths, and anything it cannot fix is marked Outdated for a human to replace or delete. The Swimm marketing and docs pages were seen via search summaries — [Swimm docs: keep docs up to date](https://docs.swimm.io/ide-integrations/vs-code/ide-plugins-vscode-keep-docs-up-to-date); [Swimm GitHub app](https://swimm.io/blog/how-swimms-github-app-works); [code-coupled docs](https://docs.swimm.io/new-to-swimm/benefits-of-code-coupled-documentation)
- Tan, Wagner, Treude: the tool detects "code element references that survive in the documentation after all source code instances have been deleted". Across more than 3,000 GitHub projects, most contained at least one outdated reference at some point. There is a GitHub Actions tool that checks on each PR (ICSME 2023) and a journal version (EMSE 29(1), 2024). These details come from a search summary of the arXiv and Monash pages — [arXiv 2212.01479](https://arxiv.org/abs/2212.01479); [Monash record](https://research.monash.edu/en/publications/wait-wasnt-that-code-here-before-detecting-outdated-software-docu/)

**Open-source agent-memory anchoring** (project READMEs and package pages via search summaries; unverified, no independent benchmarks)
- One pattern: at write time store "a normalized content hash of the anchored region (symbol body, line range, or file)". At recall, re-resolve the region ("symbols may move") and re-hash it. A changed hash marks the memory stale; a missing region marks it orphaned. legendary-mcp also records a commit per anchor, and stale memories still surface "ranked lower and clearly flagged" — [legendary-mcp](https://pypi.org/project/legendary-mcp/0.2.0/)
- limpet anchors to a normalised AST hash, so formatting and comment changes don't trigger staleness: "Rename or move the code and the memory follows, edit it and the memory goes visibly stale with a reason, revert and it heals" — [limpet](https://glama.ai/mcp/servers/KSym04/limpet)
- True Memory Fragments uses post-commit, post-merge, post-checkout and post-rewrite git hooks to produce function-level invalidation manifests. Its plugin can block agent tool calls on files with stale claims. It is a pre-release — [true-memory-fragments](https://pypi.org/project/true-memory-fragments/0.1.0rc3/); see also [code-memory-agent](https://github.com/oladri-renuka/code-memory-agent)

**Derived-index invalidation**
- Aider's tag cache is keyed on file mtime, so symbol extraction is redone only for changed files — [aider repomap.py](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py)

**Graphs for impact and localisation**
- RepoGraph (Ouyang et al., ICLR 2025):
  - Graph: line-level nodes built from tree-sitter ASTs, keeping only function- and class-related lines labelled `def` or `ref`. Edges are "invoke" (def→ref) and "contain" (def→inner parts). Built-ins and third-party relations are filtered out.
  - Retrieval: the k-hop ego-graph (k = 1 or 2) around a search term.
  - SWE-bench Lite gains: RAG 2.67 → 5.33, Agentless 27.33 → 29.67, AutoCodeRover 19.00 → 21.33, SWE-agent 18.33 → 20.33. The "average relative improvement" of 32.8% is driven by RAG doubling from a tiny base.
  — [RepoGraph full text](https://arxiv.org/html/2410.14684v2)
- LocAgent (Chen et al., Mar 2025): a "directed heterogeneous graph" of files, classes and functions with import, invoke and inherit dependencies, searched by multi-hop reasoning. It reports "up to 92.7% accuracy on file-level localization" (with fine-tuned Qwen-2.5-Coder-32B), "+12% … Pass@10" downstream, and about 86% lower cost — [arXiv 2503.09089](https://arxiv.org/abs/2503.09089)
- RepoMem (Oct 2025, ICLR 2026) — [full text](https://arxiv.org/html/2510.01003v2):
  - Episodic memory: commits with metadata and linked issues (from "Fixes #123"), restricted to commits before the issue's base commit (7,000 commits) to keep the memory time-consistent.
  - Semantic memory: LLM summaries of the top 200 most frequently edited files (the "hotspots").
  - Tools: `SearchCommit` (BM25 over commit messages), `ExamineCommit`, `ViewSummary`, `SearchSummary`.
  - Results, file Acc@1/3/5: SWE-bench Verified 64.8/70.4/71.6 → 68.6/74.5/76.5; SWE-bench-live 59.2/60.8/63.1 → 60.8/63.9/66.2. Episodic-only 67.8/72.4/74.3, semantic-only 65.0/71.0/72.8.
  - Losses: sparse-history repos ("others") went from 67.4 to 54.3 Acc@5. Results are file-level only, with a GPT-4o backbone.
- Agent Retrieval Bench (Jul 2026) includes an "edit2ripple" task type (finding files affected by an edit). Its abstract gives no per-task numbers — [arXiv 2607.24882](https://arxiv.org/abs/2607.24882)

### Inferences
- Staleness can be detected at three costs, all stdlib-reproducible:
  1. Symbol or path existence (Tan/Treude style; grep or `ast`).
  2. Region hash at write vs recall (`hashlib`, re-resolving the symbol via `ast` for Python).
  3. `git diff --name-only <recorded_sha>..HEAD` or `git log` since the record's commit, via `subprocess`. This tells you that cited files changed, not that the fact is false.

  Copilot shows the useful last step: let the agent read the cited lines and re-store or correct the memory, rather than auto-deleting it.
- Commit history is free, code-grounded episodic memory. Plain BM25 over commit messages already gave most of RepoMem's gain (episodic-only Acc@5 74.3 vs 76.5 full), and BM25 is stdlib-implementable. The file summaries need a model, so a background job.
- Impact ("what does this affect") can come from an import/def/ref graph. For Python, stdlib `ast` gives imports, defs and calls, and a reverse-dependency BFS over 2 hops matches RepoGraph's k = 1–2 ego-graphs. The measured downstream gains from such graphs are small.

### Gaps
- No study was found that measures precision or recall of staleness detection for agent memories tied to code. Copilot's adversarial test gives no numbers, and the open-source tools have no benchmarks.
- I did not verify the Tan et al. percentages or Swimm's algorithm details beyond the search-summary level.
- I did not open the RepoMem per-repository table directly. The 67.4 → 54.3 "others" figure comes from the fetch tool's reading of the paper.

## 6. Common failure modes reported for memory features: stale memories, noise, contradictions, bloat, prompt injection via memory

### Takeaway
The documented failures are:
- **Staleness**, addressed by TTLs, verification and voting (Copilot) or by not storing derivable facts (Claude Code).
- **Noise and distraction**, which made SWE agents worse in CTIM-Rover.
- **Contradictions** between instruction files, where Claude "may pick one arbitrarily".
- **Bloat and truncation**: MEMORY.md is cut at 200 lines or 25KB, and CLAUDE.md files over 200 lines reduce adherence.
- **Persistent prompt injection**, with working exploits against Windsurf memories, Cursor/Copilot rules files and Claude Code's MEMORY.md. In research settings, query-only memory injection succeeds 98% of the time and the downstream attack 77% of the time.

### Cited Findings
**Staleness**
- Copilot's 28-day expiry was introduced "to prevent stale information" — [GitHub changelog](https://github.blog/changelog/2026-01-15-agentic-memory-for-github-copilot-is-in-public-preview/). The current docs admit facts from "closed, unmerged pull requests" and that "Copilot may not catch every outdated fact" — [GitHub docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- An aggregator alert claims Claude Code 2.1.139–2.1.141 surfaced MEMORY.md content mid-task without re-verifying it against the code. I found no matching GitHub issue (unverified) — [aiweekly](https://aiweekly.co/alerts/claude-code-serves-stale-memorymd-data-mid-task)

**Noise and distraction**
- CTIM-Rover: memory-only configurations fell 11 points (42% → 31%, n = 45) because of "distracting CTIM items". Context grew from 10,027 to 17,807 median tokens — [CTIM-Rover](https://arxiv.org/html/2505.23422v1)
- Instance-level memory causes "misguided retrieval when tasks with similar surface descriptions require distinct reasoning logic" — [arXiv 2602.21611](https://arxiv.org/abs/2602.21611)
- Adding failure trajectories lowered AWM's success rate (44.4 → 42.2) — [ReasoningBank](https://arxiv.org/html/2509.25140v2)

**Contradictions**
- "If two instructions contradict each other, Claude may pick one arbitrarily". If a user rule and a project rule conflict, "Claude may follow either one" — [Claude Code memory docs](https://code.claude.com/docs/en/memory)

**Bloat, truncation, duplication**
- MEMORY.md: content past 200 lines or 25KB "is not loaded at session start". CLAUDE.md over 200 lines "reduce[s] adherence" — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Issue #23544 asked for a way to disable auto memory, citing context bloat. The premise is now out of date: `autoMemoryEnabled` and `CLAUDE_CODE_DISABLE_AUTO_MEMORY` exist — [issue #23544](https://github.com/anthropics/claude-code/issues/23544); [memory docs](https://code.claude.com/docs/en/memory)
- An issue reports auto memory duplicating CLAUDE.md content into memory files. This is from a mirror site, not github.com — [claudeissues mirror #38402](https://claudeissues.com/issue/38402-bug-claude-code-duplicates-claude-md-entries-in-its-memory-files-md)

**Product retreats**
- Cursor removed Memories in 2.1 — [Cursor forum](https://forum.cursor.com/t/are-my-memories-gone/144057). Devin deprecated Knowledge — [Devin docs](https://docs.devin.ai/product-guides/knowledge). Windsurf and Codex steer must-follow knowledge to rules or AGENTS.md — [Windsurf docs (es)](https://docs.windsurf.com/es/windsurf/cascade/memories.md); [Codex Memories](https://learn.chatgpt.com/docs/customization/memories?surface=app)

**Prompt injection via memory and rules**
- Windsurf: the `create_memory` tool is auto-invoked, so indirect injection persists across conversations ("SpAIware", 2025) — [Embrace The Red](https://embracethered.com/blog/posts/2025/windsurf-spaiware-exploit-persistent-prompt-injection)
- "Rules File Backdoor" (Pillar Security, 18 Mar 2025): "zero-width joiners, bidirectional text markers, and other invisible characters" hide instructions in Cursor and Copilot rules files from human reviewers. Cursor said "it is not a vulnerability on their side". GitHub said users are responsible, then on 1 May 2025 added a github.com warning for hidden Unicode — [Pillar Security](https://www.pillar.security/blog/new-vulnerability-in-github-copilot-and-cursor-how-hackers-can-weaponize-code-agents)
- Claude Code (Cisco, 1 Apr 2026): an npm postinstall payload overwrote `~/.claude/projects/*/memory/MEMORY.md` for every project, plus `~/.claude/settings.json` hooks and a shell alias. With the poisoned memory, Claude recommended committing an API key to source and gave no warnings. Cisco says the "first 200 lines of these files are loaded directly into the AI's system prompt" and that "as of Claude Code v2.1.50, Anthropic has included a mitigation that removes user memories from the system prompt". Anthropic's position, per Cisco, is that the user principal is fully trusted and the attack needs an untrusted repo or dependency — [Cisco blog](https://blogs.cisco.com/ai/identifying-and-remediating-a-persistent-memory-compromise-in-claude-code)
- These two descriptions are attributed separately and not merged. Cisco describes pre-v2.1.50 system-prompt loading. The current Claude Code docs say CLAUDE.md is "delivered as a user message after the system prompt" — [memory docs](https://code.claude.com/docs/en/memory)
- MINJA (Dong et al., Mar 2025; v5 Feb 2026): an attacker with query-only access plants records in a memory shared across users. Averages are 98.2% injection success and 76.8% attack success across EHRAgent, RAP and a QA agent. Embedding-level sanitisation fails because malicious and benign records are "highly entangled". Prompt-level detection with GPT-4o and a targeted prompt caught 131/135 on MIMIC-III but 0/135 on RAP and 0/90 on the QA agent — [MINJA full text](https://arxiv.org/html/2503.03704)
- From search summaries only (not opened): MemGhost (CSA note, Jul 2026) reports 71.4% end-to-end success against the Claude Code SDK with Sonnet 4.6 in background mode. PMPA (arXiv 2609.13889) induces agents to write injected instructions into persistent memory and finds prompt-level defences do little once instructions are stored — [CSA note](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/07/CSA_research_note_memghost_agent_memory_poisoning_20260723-csa-styled.pdf); [arXiv 2609.13889](https://arxiv.org/pdf/2609.13889)
- Vendor mitigations:
  - Copilot rejects memories containing secrets or "model-control tokens", and only write-permission contributors can create repository memories — [GitHub docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory); [GitHub blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
  - Codex can exclude chats that used MCP or web search from memory generation (`memories.disable_on_external_context`) — [Codex Memories](https://learn.chatgpt.com/docs/customization/memories?surface=app)
  - Claude Code asks for approval of external `@imports` in project files — [memory docs](https://code.claude.com/docs/en/memory)

### Inferences
- An automatic capture path such as a Stop-hook extractor matches the attack surface of Windsurf's `create_memory` and of MemGhost/PMPA. Defences that do not rely on the model include:
  - Provenance tags (transcript, tool output or web, user-stated).
  - Excluding turns that read external content (the Codex approach).
  - Stripping invisible Unicode (the Pillar finding).
  - Rejecting control-token-like strings.
  - Requiring write-path scripts, as opposed to free model edits, for memory files.
- Bloat and staleness fight each other: a TTL or an index limit forces forgetting, while verification needs code-linked citations. Copilot combines both (TTL refreshed by validation).

### Gaps
- No quantitative data was found on how often stale or contradictory memories cause wrong answers in production coding assistants. The evidence is anecdotal, vendor-qualitative or research-synthetic.
- Whether Windsurf patched the memory-persistence issue was not confirmed.

## 7. Which of these mechanisms can be reproduced in a local, file-based, Python-stdlib-only memory system driven by Claude Code hooks (small-model calls only in background jobs)?

### Takeaway
Nearly all the retrieval, linking and staleness machinery can be reproduced with the stdlib plus `git` via `subprocess`: a personalised-PageRank map for Python via `ast`, file:line plus hash citations with verification at recall, commit-history BM25, TTL and voting fields, symbol-existence checks, and hook-based injection and blocking. What needs a model is distillation and summarisation (ExpeL/AWM/ReasoningBank-style items, RepoMem file summaries, conflict judging), so it belongs in detached background jobs started from Stop or SessionEnd. Multi-language symbol extraction needs tree-sitter, which is not stdlib.

### Cited Findings
- Injection points:
  - UserPromptSubmit: `additionalContext` or plain stdout (≤10,000 characters, else spilled to a file with a 2,000-character preview); 30 s default timeout, with output discarded on timeout.
  - SessionStart: context only; the `compact` matcher re-injects after compaction.
  - PreToolUse: `updatedInput` and `permissionDecision: deny` for write protection.
  - PostToolUse: `additionalContext` after edits.
  - Stop: `decision: block` or `additionalContext`, plus `last_assistant_message`.
  — [hooks reference](https://code.claude.com/docs/en/hooks.md)
- Background execution: `"async": true` hooks run in the background without an enforced timeout. `prompt` and `agent` hook types are synchronous model calls (30 s and 60 s defaults) — [hooks reference](https://code.claude.com/docs/en/hooks.md)
- Compaction: hook-added context is "Summarized with the rest of the conversation", while CLAUDE.md, its imports and auto memory are re-injected from disk — [context-window page](https://code.claude.com/docs/en/context-window.md)
- Transcripts are plaintext JSONL at `~/.claude/projects/<project>/<session>.jsonl` (they include tool results and system prompts) and are deleted after 30 days by default — [.claude directory](https://code.claude.com/docs/en/claude-directory.md); [settings reference](https://code.claude.com/docs/en/settings-reference.md)
- Aider's ranking uses networkx PageRank with personalisation and a binary-search budget fit. Every weight is a simple constant (×10, ×0.1, ×50, √refs) — [aider repomap.py](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py)
- Copilot's verification is "a small number of simple read operations" — [GitHub blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- RepoMem's commit search is plain BM25 over commit messages — [RepoMem](https://arxiv.org/html/2510.01003v2)

### Inferences
**Synchronous (in-hook, stdlib)**
1. Hash-anchored citations (`hashlib` over the cited line range or the `ast` node body), checked at recall in UserPromptSubmit. Changed means "flag as possibly stale and cite the lines"; a missing file or symbol means "orphaned".
2. `git rev-parse HEAD` stored per record, plus `git diff --name-only <sha>..HEAD` to find records whose cited files changed.
3. Symbol-existence checks via `ast` or grep.
4. BM25 over commit messages and file paths (RepoMem's episodic tool).
5. Personalised PageRank over an `ast` import/def/ref graph, seeded with the files and identifiers in the prompt, for map and impact answers. Use a reverse-dependency BFS of 1–2 hops, as in RepoGraph.
6. A PostToolUse hook on Edit/Write that marks records citing the edited file for re-verification.
7. TTL, `last_validated` and vote counters as record fields, Copilot-style.
8. Re-injecting state after compaction with SessionStart `compact`.

**Background only (model)**
- Extraction or distillation of insights from transcripts, file-functionality summaries, contradiction judging, and "re-store corrected memory" proposals.
- These should run detached from Stop or SessionEnd (SessionEnd hooks have a 1.5 s budget), and should read `last_assistant_message` instead of the possibly lagging transcript file.

**Design cautions from the evidence**
- Retrieve a few relevant items rather than dumping all of them (CTIM-Rover).
- Skip storing facts the code already states (Claude Code auto-memory policy).
- Treat agent-written memory as a recall layer under human-owned rules (Windsurf, Codex, Copilot guidance).
- Tag provenance, and exclude turns that read external content, to limit persistent injection (Codex setting, Windsurf, Cisco, MINJA).

### Gaps
- No source measures the latency of hash or git verification inside a 30 s UserPromptSubmit budget on large repos. That needs a local benchmark.
- No published evaluation shows that code-linked staleness flags improve answer accuracy for project-history questions, as opposed to code-change tasks. Copilot's A/B covers PR merge rate and review feedback, not memory Q&A.
