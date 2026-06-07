# Session Prompt

Use this as the thin session-start prompt for Codex when starting a new game:

```md
Let's play a 9x9 game of Go. I play White and you play Black.

Before doing anything else:

1. Read `docs/reference/cli.md`.
2. Read `docs/agents/player/gameplay-governance.md`.
3. Use the referee CLI as the source of truth for legality, captures, ko,
   chains, liberties, move history, and board state.
4. Never manage board state by hand.
5. Never edit `game.txt` directly.

We are playing under Japanese rules with 6.5 komi.

We will communicate in short chat messages while the CLI manages the game.
Keep replies brief, report Black moves clearly, and ask for White moves in
coordinate form.

Use this command model:

- `game` is the real game
- `session` is hypothetical analysis

Record real moves only on `game`.
Use `session` for tactical reading.

When beginning a new game:

1. Initialize the canonical game with:
   - `python3 go_ref.py game init`
2. Inspect the starting state with:
   - `python3 go_ref.py game show`
   - `python3 go_ref.py game query board`
3. Choose and record Black's first move through:
   - `python3 go_ref.py game play --color black --move <MOVE>`
4. Report the move and ask for my White reply.

On each White move:

1. Record it immediately with:
   - `python3 go_ref.py game play --color white --move <MOVE>`
2. Inspect canonical state with:
   - `python3 go_ref.py game query board`
3. If analysis is needed, create a temporary session with:
   - `python3 go_ref.py session temp --from game`
4. Read candidate lines inside that session with `session play` and
   `session query`.
5. Record Black's final move only on `game`.
```

This prompt is intentionally thin. The detailed operating rules live in:

- [../../reference/cli.md](../../reference/cli.md)
- [./gameplay-governance.md](./gameplay-governance.md)
