# Go Referee CLI Reference

This document is the canonical reference for the referee CLI and its tool
contract. It describes what the tool does, what files it owns, how commands
mutate state, and how to inspect or simulate positions safely.

## Purpose

The referee is responsible for deterministic game mechanics and state
management:

- board state
- legal move checking
- captures
- connected chains and liberties
- simple ko
- pass and resignation
- undo
- tactical queries
- hypothetical move and sequence simulation
- persisted analysis branches
- generated board rendering

The referee does not provide strategy, move selection, scoring judgment, or
life-and-death verdicts.

## Analysis Modes

The repo supports three modes of use:

1. Canonical game state
   - The real game lives in `state.json` and `game.txt`.
2. Stateless tactical reading
   - `try` reads hypothetical moves and short sequences without mutating files.
3. Persisted deeper reading
   - `branch` creates named hypothetical workspaces under `analysis/branches/`.

Use the lightest tool that answers the question.

## Files

- `state.json`
  - authoritative canonical game state and primary machine-readable interface
- `game.txt`
  - generated board view for human inspection
  - not a machine interface
  - never edit directly
- `analysis/branches/<branch_name>/state.json`
  - authoritative state for one persisted hypothetical branch
- `analysis/branches/<branch_name>/game.txt`
  - rendered board view for one persisted hypothetical branch

Treat `state.json` as the live truth and `game.txt` as a rendered projection.

## Command Contract

### Mutating commands

These commands update stored state for their target and refresh the matching
rendered board:

- `init`
- `play`
- `pass`
- `resign`
- `undo`
- branch lifecycle commands that create or reset branch state

After a successful mutating command, the CLI writes updated state and refreshes
`game.txt` for that same target automatically.

### Non-mutating commands

These commands do not mutate stored state or rendered output:

- `show`
- `legal`
- `chain`
- `query`
- `try`

### Concurrency contract

Commands aimed at the same canonical game or the same branch are serialized by
the CLI so concurrent processes do not race `state.json` and `game.txt`.

## Starting A Game

```bash
python3 go_ref.py init
```

This creates or resets:

- `state.json`
- `game.txt`

Initial settings:

- board size: 9
- komi: 6.5
- handicap: 0
- Black to move

## Commands

### `show`

Print the current state as JSON.

```bash
python3 go_ref.py show
python3 go_ref.py show --branch center-fight
```

### `play`

Play a board move on canonical state or a branch.

```bash
python3 go_ref.py play --color black --move D5
python3 go_ref.py play --branch center-fight --color white --move F6
```

Move format:

- columns: `A B C D E F G H J`
- rows: `1` through `9`
- examples: `A1`, `E5`, `J9`

The tool rejects:

- off-board moves
- occupied points
- suicide, unless the move captures
- immediate recapture on the current ko point
- moves played out of turn
- moves after the game is over

### `pass`

Pass the turn.

```bash
python3 go_ref.py pass --color black
python3 go_ref.py pass --branch semeai-1 --color white
```

Behavior:

- pass is legal while the game is active
- a pass clears any ko restriction
- two consecutive passes end the game

### `resign`

Resign the game.

```bash
python3 go_ref.py resign --color white
```

Behavior:

- resignation ends the game immediately
- the board does not change

### `legal`

List all legal board moves for a color:

```bash
python3 go_ref.py legal --color black
```

Check one specific move:

```bash
python3 go_ref.py legal --color black --move D5
```

This command is for mechanical legality only.

### `chain`

Inspect the chain and liberties at a point.

```bash
python3 go_ref.py chain --point D4
```

Use `query chain` when you want richer tactical context.

### `query`

Ask structured tactical questions without changing state.

Inspect one point:

```bash
python3 go_ref.py query point --point E5
```

Inspect a chain with adjacent-chain data:

```bash
python3 go_ref.py query chain --point D4
```

Summarize all chains and empty regions:

```bash
python3 go_ref.py query board
```

Every `query` command also accepts `--branch <name>`.

### `try`

Read hypothetical lines without mutating canonical or branch files.

Try one move:

```bash
python3 go_ref.py try play --color black --move E4
```

Get a structured legality explanation:

```bash
python3 go_ref.py try legality --color black --move E4
```

Try a short sequence:

```bash
python3 go_ref.py try sequence --moves "B:E4,W:D4,B:F4"
```

Every `try` command also accepts `--branch <name>`.

### `branch`

Manage persisted hypothetical branches.

Create a branch from canonical:

```bash
python3 go_ref.py branch create --name semeai-1
```

Create a branch from another branch:

```bash
python3 go_ref.py branch create --name ko-read --from-branch semeai-1
```

List branches:

```bash
python3 go_ref.py branch list
```

Show one branch:

```bash
python3 go_ref.py branch show --name semeai-1
```

Reset a branch from canonical:

```bash
python3 go_ref.py branch reset --name semeai-1 --from canonical
```

Reset a branch from another branch:

```bash
python3 go_ref.py branch reset --name ko-read --from branch --source semeai-1
```

Delete a branch:

```bash
python3 go_ref.py branch delete --name ko-read
```

Branch commands never mutate canonical `state.json` or `game.txt`.

### `validate`

Validate that the stored state is internally consistent.

```bash
python3 go_ref.py validate
python3 go_ref.py validate --branch center-fight
```

This checks:

- board shape
- move log consistency
- last move consistency
- ko validity
- replay consistency from the move log

### `render`

Regenerate `game.txt` from the current state.

```bash
python3 go_ref.py render
python3 go_ref.py render --branch center-fight
```

Use this to refresh a rendered board view without changing state. You should
not need this after a successful `play`, `pass`, `resign`, or `undo`, because
those commands already refresh the rendered board for their target.

### `undo`

Undo the most recent move:

```bash
python3 go_ref.py undo
python3 go_ref.py undo --branch center-fight
```

Undo multiple moves:

```bash
python3 go_ref.py undo --count 2
```

This rewinds state and refreshes the rendered board view for that target.

## Output Conventions

All commands are designed for tool-assisted use.

- stdout
  - JSON only
- stderr
  - human-readable diagnostics
- exit code
  - `0` on success
  - nonzero on failure
