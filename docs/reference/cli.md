# Go Referee CLI Reference

This document is the canonical reference for the referee CLI and its contract.

## Purpose

The referee is responsible for deterministic mechanics and state management:

- board state
- legal move checking
- captures
- connected chains and liberties
- simple ko
- pass and resignation
- undo
- tactical queries
- generated board rendering
- persistent and ephemeral analysis sessions

The referee does not choose moves, rank candidates, or judge score.

## Player Workflow At A Glance

For real play, the default routine is:

1. Record real moves on `game`.
2. Inspect canonical state with `game query`.
3. Create a `session` for hypothetical reading.
4. Play and query candidate lines inside that session.
5. Record the final chosen move back on `game`.

Example:

```bash
python3 go_ref.py game play --color white --move D5
python3 go_ref.py game query board
python3 go_ref.py session temp --from game
python3 go_ref.py session play --name _tmp_ab12cd34 --color black --move C3
python3 go_ref.py session query --name _tmp_ab12cd34 board
python3 go_ref.py game play --color black --move C3
```

The key rule is:

- `game` is real
- `session` is hypothetical

## Targets

The CLI exposes two target types.

### `game`

The canonical game lives in:

- `state.json`
- `game.txt`

### `session`

Analysis sessions live in:

- `analysis/sessions/<name>/state.json`
- `analysis/sessions/<name>/game.txt`
- `analysis/sessions/<name>/meta.json`

Sessions may be:

- `persistent`
- `ephemeral`

## Command Contract

### Mutating commands

These update stored state for their target and refresh the matching rendered
board:

- `game init`
- `game play`
- `game pass`
- `game resign`
- `game undo`
- `session create`
- `session temp`
- `session play`
- `session pass`
- `session resign`
- `session undo`
- `session reset`
- `session persist`

### Non-mutating commands

These do not mutate stored state:

- `game show`
- `game legal`
- `game chain`
- `game query`
- `session show`
- `session list`
- `session legal`
- `session chain`
- `session query`

### Concurrency contract

Commands aimed at the same canonical game or the same session are serialized by
the CLI so concurrent processes cannot race `state.json` and `game.txt`.

## Canonical Game Commands

Start or reset the canonical game:

```bash
python3 go_ref.py game init
```

Inspect canonical state:

```bash
python3 go_ref.py game show
python3 go_ref.py game query board
python3 go_ref.py game chain --point E5
```

Mutate canonical state:

```bash
python3 go_ref.py game play --color black --move E5
python3 go_ref.py game pass --color white
python3 go_ref.py game resign --color black
python3 go_ref.py game undo --count 1
```

Other canonical helpers:

```bash
python3 go_ref.py game legal --color black
python3 go_ref.py game legal --color black --move E5
python3 go_ref.py game validate
python3 go_ref.py game render
```

## Session Commands

Create a persistent session from canonical state:

```bash
python3 go_ref.py session create --name center-read
```

Create a persistent session from another session:

```bash
python3 go_ref.py session create --name ko-read --from session:center-read
```

Create an ephemeral session:

```bash
python3 go_ref.py session temp --from game
```

List sessions:

```bash
python3 go_ref.py session list
```

Inspect or mutate a session:

```bash
python3 go_ref.py session show --name center-read
python3 go_ref.py session play --name center-read --color black --move D4
python3 go_ref.py session query --name center-read board
python3 go_ref.py session undo --name center-read --count 1
```

The session query syntax is intentionally consistent:

```bash
python3 go_ref.py session query --name center-read board
python3 go_ref.py session query --name center-read point --point E5
python3 go_ref.py session query --name center-read chain --point D4
```

Reset, persist, or delete:

```bash
python3 go_ref.py session reset --name center-read --from game
python3 go_ref.py session persist --name _tmp_ab12cd34 --as saved-read
python3 go_ref.py session delete --name center-read
```

## Query Subcommands

Both `game query` and `session query` support:

```bash
python3 go_ref.py game query point --point E5
python3 go_ref.py game query chain --point D4
python3 go_ref.py game query board
```

and:

```bash
python3 go_ref.py session query --name center-read point --point E5
python3 go_ref.py session query --name center-read chain --point D4
python3 go_ref.py session query --name center-read board
```

## Move Format

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

## JSON Output

All CLI commands print machine-readable JSON on stdout.

Successful responses include:

- `ok: true`
- `command`
- `result`

Mutating and query responses include a `target` object in `result` describing
which game or session was addressed.

Errors print a short human message on stderr and machine-readable JSON on
stdout with:

- `ok: false`
- `command`
- `error.code`
- `error.message`
- `error.details`
