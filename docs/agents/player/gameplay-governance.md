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

## Command Ordering

- Do not start a same-target read concurrently with a write it depends on.
- If a later command must observe the result of an earlier command on the same
  `game` or `session`, wait for the earlier command to finish before starting
  the next one.
- Use parallel execution only for independent work or for commands aimed at
  different targets.

Examples:

- good: `game play`, wait for completion, then `game query board`
- good: `game query board` while separately reading docs or inspecting another
  unrelated file
- bad: launching `game play` and `game query board` together when the query is
  meant to reflect that move

## Start Of Game

When beginning a new game:

1. Initialize canonical state:

```bash
python3 go_ref.py game init
```

This also clears any leftover analysis sessions from earlier games.

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

Use `session` to think before you commit, but do not turn analysis into a
ritual. The important ground rules are:

1. Record White's real move immediately on `game`.
2. Inspect the updated canonical position with `game query board`.

After that, let the position determine the reading. In general:

- use `session` when Black needs tactical reading
- keep reading while the local fight is forcing or unstable
- compare sharp moves against calmer shape when the forcing line fizzles
- record Black's chosen move on `game` only after the choice is clear enough

This is not a move-selection algorithm. The point is to keep real play and
hypothetical reading separate while giving Codex room to judge shape, life,
efficiency, and whole-board tradeoffs.

## Forced-Line Reading

Forced-line reading is required when the position is tactically hot, especially
if a candidate move or White's obvious reply:

- captures stones
- gives atari
- answers atari
- creates or resolves ko
- leaves the newly played Black chain or an adjacent Black chain with 1 or 2
  liberties

During forced-line reading, keep following the branch while either side still
has an obvious forcing move involving the same local chain or capture race.

For this protocol, a forcing move means a move that:

- captures
- puts the target chain in atari
- answers atari
- prevents immediate capture
- creates or resolves ko

Use `session` to continue the line until one of these is true:

- the target chain is captured
- the target chain is no longer under immediate forcing pressure
- both sides have multiple plausible non-forcing choices
- the line repeats or becomes a ko or branch problem
- the read reaches a configured depth limit and must be summarized as
  unresolved

Reject a candidate if the forced-line read shows Black remains under pressure
without getting enough in return.

For this rule, "concrete gain" is Codex's tactical judgment about the branch
result. It is not referee output and must not be inferred from the CLI as a
move recommendation or life-and-death judgment.

## Candidate Discipline

Do not treat a move as good merely because it:

- reduces an enemy chain's liberties
- creates an atari threat that White can answer comfortably
- looks active or severe for one ply

Before trusting a sharp local move, read White's strongest obvious local reply
first. This matters most when Black's move:

- leans on a chain without taking liberties away to 1 immediately
- creates a new Black chain with only 1 or 2 liberties
- invites an immediate atari on the newly played Black chain
- starts a contact fight next to an already unsettled Black chain

Be suspicious of the candidate if White's best reply:

- drives Black into an immediate defensive sequence
- lets White connect or extend while Black gains no capture, thickness, or
  stable shape
- leaves Black less settled than a calmer alternative after the forcing
  sequence ends

When a sharp candidate fizzles, prefer the calmer move that leaves Black with
better shape or a cleaner position.

Do not confuse short-term severity with profit. A move that looks active for
one ply may still be poor if White's natural answer leaves Black heavy, thin,
or forced low.

Likewise, do not stop reading just because Black found a legal move that saves
one stone or answers one atari. Continue until the local fight is actually
stable, or until the candidate is clearly worse than a quieter alternative.

## Recording Black's Final Move

Once analysis is complete, record the chosen move on canonical state:

```bash
python3 go_ref.py game play --color black --move J7
```

Then stop analysis, report the move clearly, and ask White for the next move.

Do not leave the final move only inside a session.

## Practical Routine

As a default rhythm during real play:

1. Put White's move on `game`.
2. Inspect the canonical position.
3. Use `session` for any tactical reading Black needs.
4. Keep reading while the local position is forcing or unstable.
5. Commit the real Black move on `game` once the choice is clear enough.

Use this rhythm unless the move is trivially forced, a pass, or a resignation.

## Communication Rules

- Keep replies brief.
- Report Black moves clearly.
- Ask for White's move in coordinate form such as `C3`.
- Do not dump large JSON outputs to the user unless specifically needed.
- If a White move is illegal, explain briefly and ask for another move.
