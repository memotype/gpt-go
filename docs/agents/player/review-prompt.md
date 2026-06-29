# Review Prompt

Use this as the thin prompt for reviewing a completed game:

This prompt is intentionally thin. The detailed review rules live in:

- `docs/reference/cli.md`
- `docs/agents/player/gameplay-governance.md`
- `docs/agents/player/evaluation-rubric.md`

## PROMPT

```md
Review this completed 9x9 Go game played with the referee repo.

Before doing anything else:

1. Read `docs/reference/cli.md` if needed for factual board inspection.
2. Read `docs/agents/player/gameplay-governance.md`.
3. Read `docs/agents/player/evaluation-rubric.md`.

Use the referee CLI as the source of truth for board state, move history,
chains, liberties, captures, and rendered output. Do not manage board state by
hand.

Review the game as a post-game analysis, not as a live move-selection task.
Focus on Black's judgment patterns.

Identify:

- Black's best move
- Black's worst move
- the first move where Black drifted into local inertia, if any
- the main recurring failure mode
- the main positive pattern
- the governance lesson suggested by this game

Use the rubric to comment on urgency judgment, whole-board resets, life and
settling, profit and territory, candidate breadth, attack quality, and
recurring anti-patterns.
```

When summarizing, keep the review concrete:

- cite move numbers
- describe the board consequence
- explain the recurring thought pattern, not just the surface mistake
