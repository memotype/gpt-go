# Codex Player Docs

These docs describe how Codex should operate when it is playing a Go game with
this repo's tools.

Read these first:

1. [../../reference/cli.md](../../reference/cli.md)
   - referee and CLI contract, plus concrete `game`/`session` command examples
2. [./gameplay-governance.md](./gameplay-governance.md)
   - move discipline, urgency classification, adversarial candidate rejection,
     breadth-before-depth comparison, whole-board resets, life/base/territory
     judgment, session-based reading hygiene, attack-minded punishment of
     overplay, anti-inertia guardrails, and concrete vetoes for hollow
     tactical or shape-worsening saves
3. [./session-prompt.md](./session-prompt.md)
   - thin copy-pasteable prompt for starting a live game session
4. [./evaluation-rubric.md](./evaluation-rubric.md)
   - post-game review rubric for urgency, whole-board judgment, life, profit,
     anti-patterns, and governance lessons
5. [./review-prompt.md](./review-prompt.md)
   - thin copy-pasteable prompt for post-game review sessions
