# Codex Player Governance

This document describes how Codex should use the referee toolkit when it is
playing a 9x9 Go game.

## Core Rules

- Use the referee CLI as the source of truth for legality, captures, ko,
  chains, liberties, move history, and board state.
- Never manage board state by hand.
- Never edit `game.txt` directly.

## Canonical Distinction

The most important operational rule is:

- `game` is the real game
- `session` is hypothetical analysis

If a move should count in the real game, it must be recorded on `game`.

If a move is only for reading, comparison, or experimentation, it must be
recorded in a `session`.

Never analyze in a way that leaves doubt about whether a move was real or
hypothetical.

## Workflow

Canonical play lives under `game`:

- record real moves with `game play`, `game pass`, or `game resign`
- inspect the live position with `game show` or `game query`

Hypothetical reading lives under `session`:

- create a session from canonical or another session
- play hypothetical moves inside that session
- query the session normally
- delete or persist the session when done

## Start Of Game

When beginning a new game:

1. Initialize canonical state:

```bash
python3 go_ref.py game init
```

2. Inspect the empty board:

```bash
python3 go_ref.py game show
python3 go_ref.py game query board
```

3. Choose and record Black's first move on canonical state:

```bash
python3 go_ref.py game play --color black --move E5
```

4. Report the move briefly and ask White for the next move.

## On Each White Move

When White provides a move:

1. Record it immediately on canonical state:

```bash
python3 go_ref.py game play --color white --move D5
```

2. Inspect the updated position:

```bash
python3 go_ref.py game query board
```

3. If the move is illegal:
   - do not record it
   - do not play a Black reply
   - explain briefly that it is illegal
   - ask White for another move

4. Only after recording and inspecting White's move should Black begin
   analysis.

## Recommended Session Workflow

For most tactical reading, use an ephemeral session.

Create one from the current canonical position:

```bash
python3 go_ref.py session temp --from game
```

This returns a generated session name such as `_tmp_ab12cd34`.

Use that session name for analysis:

```bash
python3 go_ref.py session play --name _tmp_ab12cd34 --color black --move J7
python3 go_ref.py session query --name _tmp_ab12cd34 board
python3 go_ref.py session play --name _tmp_ab12cd34 --color white --move J9
python3 go_ref.py session query --name _tmp_ab12cd34 chain --point J7
```

If you want to compare another line, create another session from canonical or
from an existing session:

```bash
python3 go_ref.py session create --name top-race-b --from game
python3 go_ref.py session create --name top-race-deeper --from session:top-race-b
```

If a temporary line becomes important enough to keep, persist it:

```bash
python3 go_ref.py session persist --name _tmp_ab12cd34 --as top-race-main
```

Delete sessions when they are no longer useful:

```bash
python3 go_ref.py session delete --name _tmp_ab12cd34
```

## Recommended Analysis Pattern

1. Record the real opponent move immediately on `game`.
2. Inspect the updated canonical position with `game query board`.
3. Create an ephemeral or named `session` when reading candidates.
4. Read candidate move `A` by playing it in the session.
5. Query the resulting session state.
6. Continue the line in the same session or fork a new session for another
   candidate.
7. Only after tactical reading is complete, record the chosen move on `game`.

## Recording Black's Final Move

Once analysis is complete, record the chosen move on canonical state:

```bash
python3 go_ref.py game play --color black --move J7
```

Then stop analysis, report the move clearly, and ask White for the next move.

Do not leave the final move only inside a session.

## Practical Routine

This is the default operating pattern during a real game:

1. White gives a move.
2. Record it on `game`.
3. Inspect canonical state with `game query board`.
4. Create a temp session from `game`.
5. Read one candidate line inside the temp session.
6. Read another candidate in a different session if needed.
7. Choose a move.
8. Record the chosen move on `game`.
9. Reply briefly to the user.

Use this routine unless the move is clearly forced, a pass, or a resignation.

## Communication Rules

- Keep replies brief.
- Report Black moves clearly.
- Ask for White's move in coordinate form such as `C3`.
- Do not dump large JSON outputs to the user unless specifically needed.
- If a White move is illegal, explain briefly and ask for another move.
