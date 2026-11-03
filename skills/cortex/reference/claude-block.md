# CORTEX `CLAUDE.md` block (v5)

The rules themselves live in `reference/rules.md`. At build or upgrade, copy that file to `memory/RULES.md` (byte for byte; never edit the copy) and insert the stub below into the project's `CLAUDE.md`. Every import is inside the project, so Claude Code shows no approval dialog, and the stub works for global installs, `--project` installs and `CLAUDE_CONFIG_DIR` alike.

**Placeholder:** `{{SKILL_DIR}}`: the skill's resolved absolute path (the value of `${CLAUDE_SKILL_DIR}`), e.g. `/Users/name/.claude/skills/cortex`. Never write `~` or a variable; `CLAUDE.md` doesn't expand them.

On upgrade, replace everything from `<!-- CORTEX:BEGIN` to `<!-- CORTEX:END -->`. Move any project-specific lines found inside the old block to the project's own section of `CLAUDE.md`, outside the markers.

=====
<!-- CORTEX:BEGIN v5 -->
## Project memory (CORTEX) · skill: `{{SKILL_DIR}}`
@memory/RULES.md
@memory/INDEX.md
@memory/team/user-preferences.md

If the CORTEX memory rules are not in your context above, read `memory/RULES.md` before doing anything else.
<!-- CORTEX:END -->
=====

**Paused stub** (`/cortex pause --read --project`): replaces the block above until `/cortex resume --read --project` puts it back. It imports nothing, so new chats load no memory. Keep `{{SKILL_DIR}}` as it was; fill `{{SINCE}}` with the local date and time.

=====
<!-- CORTEX:BEGIN v5 paused-read -->
## Project memory (CORTEX) · skill: `{{SKILL_DIR}}` · paused
Memory is paused for this project since {{SINCE}}: don't read, search, cite or write `memory/`. `/cortex resume --read --project` turns it back on.
<!-- CORTEX:END -->
=====

**Inline fallback** (`/cortex config rules=inline`, for tools that don't follow `@` imports): replace the `@memory/RULES.md` line with the full contents of `memory/RULES.md`.

Don't put the stub in `AGENTS.md` or other tools' instruction files: they may not follow `@` imports. Leave such files as they are and mention them to the user.
