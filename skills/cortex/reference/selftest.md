# CORTEX self-test

Checks that memory can still answer what was recently decided and rejected, and repairs it where it can't. It runs on its own when the SessionStart hook says it's due (after 5 changed session logs, at most once a day), or on `/cortex selftest`. It edits memory only: never `RULES.md`, never project code.

`<skill>` is this skill's folder; `<project>` is the project root.

1. **Pick facts:** `python3 <skill>/scripts/selftest.py <project>` (`--all` for a manual run). It prints up to 10 recent decisions and rejections as JSON, each with its source line. If it prints no facts, record `0/0` (step 6) and stop.
2. **Write questions** a teammate might naturally ask, one per fact, without giving the answer away. Skip facts too trivial to matter (e.g. "the user cut the research short"). A rejection becomes a suggestion ("Should we use X for Y?"); a decision becomes a question about what or why ("How do we handle Y, and why?"). Keep each question's fact and source to yourself.
3. **Ask a fresh examinee.** Start one background agent and keep working on the user's request while it runs. Give it only the questions and this brief:
   > You are a fresh Claude session in `<project>`. Read `CLAUDE.md` there, then every file it imports with `@` (paths relative to the project); treat them as your instructions. Answer each question below using `memory/` exactly as those rules say. Don't modify any file. For each question give your answer in two sentences at most, and the memory files you opened or grepped.
4. **Grade each answer** against its fact. It passes if it gets the decision or rejection right and gives its reason. "Not found", a wrong answer, or a re-proposed rejected option is a miss.
5. **Repair each miss at its cause.** Check in this order:
   - The fact is in no L1 file: add it to the owning L1 file, with its source tag (rejections as `Rejected: <option> (<why>) <tag>`).
   - It's in an L1 file the examinee never opened: add the question's key nouns to that file's line in the map.
   - The map pointed the examinee elsewhere: fix that map line.
   Don't add duplicates. A fact already correct in L1 needs only the map fix.
   Then fix the gaps the examinee reports even where it answered correctly (a rejection held only in a session log, an important L1 line without a source tag): they are the next misses waiting to happen.
6. **Record the result:** append one line to `memory/log/selftest.md` (create the file with a `# Self-test history` heading if it's missing). Format:
   `- YYYY-MM-DD HH:MM · <passed>/<asked> · fixed: <what, or none> · logs: <n>`
   Then print `⟦CORTEX⟧ selftest ▸ <passed>/<asked> recalled · fixed <n> (<files>)` for the user.
