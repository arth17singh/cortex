# CORTEX `CLAUDE.md` block (v7)

The rules themselves live in `reference/rules.md`. At build or upgrade, copy that file to `memory/RULES.md` (byte for byte; never edit the copy) and insert the stub below into the project's `CLAUDE.md`. Every import is inside the project, so Claude Code shows no approval dialog, and the stub works for global installs, `--project` installs and `CLAUDE_CONFIG_DIR` alike.

**Placeholder:** `{{SKILL_DIR}}`: the skill's resolved absolute path (the value of `${CLAUDE_SKILL_DIR}`), e.g. `/Users/name/.claude/skills/cortex`. Never write `~` or a variable; `CLAUDE.md` doesn't expand them.

On upgrade, replace everything from `<!-- CORTEX:BEGIN` to `<!-- CORTEX:END -->`. Move any project-specific lines found inside the old block to the project's own section of `CLAUDE.md`, outside the markers.

=====
<!-- CORTEX:BEGIN v7 -->
## Project memory (CORTEX) · skill: `{{SKILL_DIR}}`
@memory/RULES.md
@memory/INDEX.md
@memory/GRAPH.md
@memory/team/user-preferences.md

If the CORTEX memory rules are not in your context above, read `memory/RULES.md` before doing anything else.
<!-- CORTEX:END -->
=====

**Reading-off stub** (`/cortex pause --read --project`): replaces the block until `/cortex resume --read --project` puts it back. It imports only the rules, so new chats know how to record but load no memory into context. Keep `{{SKILL_DIR}}`; fill `{{SINCE}}` with the local date and time.

=====
<!-- CORTEX:BEGIN v7 paused-read -->
## Project memory (CORTEX) · skill: `{{SKILL_DIR}}` · reading off
@memory/RULES.md

Memory reading is off for this project since {{SINCE}}: don't open, search or cite memory for an answer, and write no recall line. Keep recording: open the session log, `memory/INDEX.md` and the owning topic file only to write to them. `/cortex resume --read --project` turns reading back on.
<!-- CORTEX:END -->
=====

**Off stub** (`/cortex off --project`): replaces the block until `/cortex on --project` puts it back. It imports nothing, so new chats neither load nor save memory, and the hooks stay quiet.

=====
<!-- CORTEX:BEGIN v7 cortex-off -->
## Project memory (CORTEX) · skill: `{{SKILL_DIR}}` · off
CORTEX is off for this project since {{SINCE}}: don't read, search, cite or write `memory/`. `/cortex on --project` turns it back on.
<!-- CORTEX:END -->
=====

**Inline fallback** (`/cortex config rules=inline`, for tools that don't follow `@` imports): replace the `@memory/RULES.md` line with the full contents of `memory/RULES.md`.

**Hooks (v7):** register the five command hooks from `reference/hooks-v7.json` in the project's `.claude/settings.json` (or the user's, at install), with `{{SKILL_DIR}}` filled in. Every hook exits at once outside CORTEX projects and inside CORTEX's own nested `claude -p` calls (`CORTEX_NESTED`).

Don't put the stub in `AGENTS.md` or other tools' instruction files: they may not follow `@` imports. Leave such files as they are and mention them to the user.
