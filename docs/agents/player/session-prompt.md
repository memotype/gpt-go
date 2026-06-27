# Session Prompt

Use this as the thin session-start prompt for Codex when starting a new game:

This prompt is intentionally thin. The detailed operating rules live in:

- `docs/reference/cli.md`
- `docs/agents/player/gameplay-governance.md`

## PROMPT

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
Two consecutive passes enter scoring, not irreversible termination.
If play should continue after a scoring dispute, use `resume` rather than
undoing the passes.
If no more play should occur after scoring, use `finalize`.

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
   - If two consecutive passes occur during real play or in a session, treat
     that state as scoring; use `game resume` or `session resume` if play must
     continue, or `game finalize` / `session finalize` if the line is truly
     complete.
   - If a candidate move or reply starts a forcing sequence, continue reading
     in `session` until the forcing sequence ends, repeats, becomes a ko or
     branch problem, or reaches the configured depth limit.
   - If a move is meant to defend a weak Black chain, query the resulting
     chain after the move instead of assuming that connection created safety.
   - Do not stop after one legal-looking reply while the opponent still has an
     obvious forcing atari, capture, ko recapture, or immediate threat
     involving the same chain.
   - Do not trust one-ply severity by itself. Read White's strongest obvious
     local reply first, and prefer the move that leaves Black with the better
     shape or cleaner result after that reply.
   - Before treating a nearby local issue as mandatory, classify it as
     `forced`, `contestable`, or `open`.
   - Do not treat a move as a successful defense if it only connects an
     endangered Black chain into a larger chain that still has 1 liberty, or
     still faces the same forcing attack after White's strongest local reply.
   - When a local line stops being forcing, compare at least one outward or
     non-local candidate instead of defaulting to another nearby maintenance
     move.
   - Be suspicious of repeated local investment or interior-fill moves unless
     they create a concrete result such as a capture, escape, boundary, or
     forcing trade.
   - Do not justify a move as safe, thick, or calm unless you can name the
     concrete board change it creates.
   - After captures, major connections, or failed local plans, briefly reset
     and reassess the whole board before continuing the previous idea by
     inertia.
5. Record Black's final move only on `game`.
```
