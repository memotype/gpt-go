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
- scoring-phase resume and finalize
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
- `game resume`
- `game finalize`
- `game undo`
- `session create`
- `session temp`
- `session play`
- `session pass`
- `session resign`
- `session resume`
- `session finalize`
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

For single-target commands, the CLI also preserves arrival order. If `game play`
reaches the referee before `game query board` on the same target, the query
will observe that move rather than an earlier snapshot.

## Canonical Game Commands

Start or reset the canonical game:

```bash
python3 go_ref.py game init
```

`game init` also clears any existing analysis sessions so a new canonical game
starts with a fresh analysis workspace.

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
python3 go_ref.py game resume
python3 go_ref.py game finalize
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
python3 go_ref.py session resume --name center-read
python3 go_ref.py session finalize --name center-read
python3 go_ref.py session persist --name _tmp_ab12cd34 --as saved-read
python3 go_ref.py session delete --name center-read
```

## Lifecycle Status

- `active`
  - normal play; `play`, `pass`, `resign`, and `undo` are allowed
- `scoring`
  - entered automatically after two consecutive passes
  - normal play is paused; inspection commands still work
  - `play`, `pass`, and `resign` are rejected
  - use `resume` to continue play without deleting the pass history
  - use `finalize` to mark the game finished without changing the board
- `finished`
  - terminal after resignation or explicit finalization
  - inspection commands still work
  - `play`, `pass`, `resign`, `resume`, and `finalize` are rejected
  - `undo` remains available as a correction tool

Turn order remains consistent through scoring. After `Black pass` then `White
pass`, Black is next if play later resumes.

## Status-Sensitive Command Rules

- `show`, `query`, and `chain` stay non-mutating and remain available in all
  lifecycle states.
- `legal` stays non-mutating in all lifecycle states.
  - in `active`, it reports legal play normally
  - in `scoring` and `finished`, point checks return `legal: false` with a
    status-based reason, and list mode returns no legal moves with
    `pass_legal: false`
- `undo` remains available in `active`, `scoring`, and `finished`.
- `resume` is valid only in `scoring`.
- `finalize` is valid only in `scoring`.

## Query Subcommands

Both `game query` and `session query` support:

```bash
python3 go_ref.py game query point --point E5
python3 go_ref.py game query point --point E5 --local-radius 2
python3 go_ref.py game query chain --point D4
python3 go_ref.py game query chain --point D4 --local-radius 1
python3 go_ref.py game query board
python3 go_ref.py game query board --include-last-event
python3 go_ref.py game query board --include-low-liberty --liberty-threshold 2
```

and:

```bash
python3 go_ref.py session query --name center-read point --point E5
python3 go_ref.py session query --name center-read point --point E5 \
  --local-radius 2
python3 go_ref.py session query --name center-read chain --point D4
python3 go_ref.py session query --name center-read chain --point D4 \
  --local-radius 1
python3 go_ref.py session query --name center-read board
python3 go_ref.py session query --name center-read board --include-last-event
python3 go_ref.py session query --name center-read board \
  --include-low-liberty --liberty-threshold 2
```

Additional query flags stay factual and non-mutating:

- `--local-radius N`
  - available on `query point` and `query chain`
  - returns a structured local crop centered on the queried point
  - valid range: `1` through `4`
- `--include-last-event`
  - available on `query board`
  - includes a compact factual summary of chains and points changed by the last
    event when history exists
- `--include-low-liberty`
  - available on `query board`
  - includes a factual list of chains at or below a liberty threshold
- `--liberty-threshold N`
  - available on `query board`
  - defaults to `2`
  - must be at least `1`

The additive query payloads remain descriptive only. They expose local state,
chain structure, and factual diffs without recommending moves or ranking
candidates.

### `query point`

Base fields include:

- `point`
- `occupant`
- `neighbors`
- `empty_neighbor_count`
- `friendly_neighbors`
- `enemy_neighbors`
- `move_effects`
- `touching_chain_anchors`

When the point is occupied, `chain` also includes:

- `color`
- `anchor`
- `stones`
- `liberties`
- `liberty_count`
- `in_atari`

`touching_chain_anchors` reports only adjacent chains:

- on empty points:
  - `black`
  - `white`
- on occupied points:
  - `occupied_chain`
  - `friendly`
  - `enemy`

For legal hypothetical plays in `move_effects[color]`, `preview` includes:

- `played_chain`
- `board_diff`
- `adjacent_enemy_chains_after_play`
- `capture_count_delta`
- `ko_point_after`

If `--local-radius` is provided, `local_view` includes:

- `center`
- `radius`
- `bounds`
- `rows`

Each local-view cell reports:

- `coord`
- `occupant`
- `is_center`
- `is_last_move`

### `query chain`

Base fields include:

- `point`
- `occupant`
- `chain`
- `liberties`
- `liberty_count`
- `in_atari`
- `chain_anchor`
- `adjacent_enemy_chains`
- `adjacent_friendly_chains`
- `shared_liberties`

Adjacent chain entries include:

- `anchor`
- `stones`
- `liberties`
- `liberty_count`
- `in_atari`

If `--local-radius` is provided, `local_view` uses the same shape as
`query point`.

### `query board`

Base fields include:

- `side_to_move`
- `status`
- `ko_point`
- `capture_counts`
- `chain_summary`
- `chains`
- `empty_regions`

Each chain entry includes:

- `anchor`
- `color`
- `stones`
- `liberties`
- `liberty_count`
- `in_atari`
- `adjacent_enemy_chain_anchors`

When requested, additive board fields include:

- `last_event_summary`
  - `event`
  - `placed_point`
  - `captured_points`
  - `changed_points`
  - `changed_chain_anchors`
  - `changed_chains`
- `low_liberty_chains`

Each `changed_chains` entry reports:

- `anchor_before`
- `anchor_after`
- `color`
- `status`
- `stones_before`
- `stones_after`
- `liberty_count_before`
- `liberty_count_after`

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
- moves when lifecycle status forbids ordinary play, such as `scoring` or
  `finished`

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
