# Go Referee CLI

This repo provides a small command-line referee for 9x9 Go. It is meant to support a Codex session that is playing a game while delegating board-state enforcement to a deterministic tool.

The tool manages:
- board state
- legal move checking
- captures
- connected chains and liberties
- simple ko
- pass and resignation
- undo
- a human-readable `game.txt`

The tool does not provide:
- move recommendations
- strategy
- candidate ranking
- life/death judgment
- ladder reading
- territory or score estimation during play

## Files You Use

- `state.json`
  - Authoritative game state.

- `game.txt`
  - Generated board view for human inspection.

You should treat `state.json` as the live truth and `game.txt` as a rendered view.

## Starting a Game

Initialize a fresh 9x9 game:

```bash
python3 go_ref.py init
```

This creates or resets:
- `state.json`
- `game.txt`

The initial settings are:
- board size: 9
- komi: 6.5
- handicap: 0
- Black to move

## Normal Session Flow

Typical play loop:

1. Initialize the game:

```bash
python3 go_ref.py init
```

2. Inspect the board:

```bash
python3 go_ref.py show
```

or open `game.txt` in your editor.

3. Play moves through the referee:

```bash
python3 go_ref.py play --color black --move E5
python3 go_ref.py play --color white --move C3
```

4. Repeat until the game ends by two consecutive passes or resignation.

## Commands

### `init`

Create a fresh game state and render the initial board.

```bash
python3 go_ref.py init
```

### `show`

Print the current state as JSON.

```bash
python3 go_ref.py show
```

Use this when a Codex session needs the exact structured state instead of visually reading `game.txt`.

### `play`

Play a board move.

```bash
python3 go_ref.py play --color black --move D5
python3 go_ref.py play --color white --move F6
```

Move format:
- columns: `A B C D E F G H J`
- rows: `1` through `9`
- examples: `A1`, `E5`, `J9`

The tool will reject:
- off-board moves
- occupied points
- suicide, unless the move captures
- immediate recapture on the current ko point
- moves played out of turn
- moves after the game is over

After a legal move, the tool updates both `state.json` and `game.txt`.

### `pass`

Pass the turn.

```bash
python3 go_ref.py pass --color black
python3 go_ref.py pass --color white
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

This command is for mechanical legality only. It does not evaluate which legal move is better.

### `chain`

Inspect the chain and liberties at a point:

```bash
python3 go_ref.py chain --point D4
```

This is useful for:
- confirming connected stones
- checking current liberties
- understanding a capture result

### `validate`

Validate that the stored state is internally consistent.

```bash
python3 go_ref.py validate
```

This checks things like:
- board shape
- move log consistency
- last move consistency
- ko validity
- replay consistency from the move log

### `render`

Regenerate `game.txt` from the current state.

```bash
python3 go_ref.py render
```

Use this if you want to refresh the human-readable board view without changing state.

### `undo`

Undo the most recent move:

```bash
python3 go_ref.py undo
```

Undo multiple moves:

```bash
python3 go_ref.py undo --count 2
```

This rewinds state and regenerates `game.txt`.

## Output Conventions

All commands are designed for tool-assisted use.

- stdout:
  - JSON only

- stderr:
  - human-readable diagnostics

- exit code:
  - `0` on success
  - nonzero on failure

This means a Codex session should read stdout for structured results and use stderr only for brief failure context.

## Reading `game.txt`

The rendered board uses:
- `.` for empty intersections
- `X` for Black
- `O` for White
- `+` for empty hoshi points
- `~` for the current ko-forbidden point
- `(X)` or `(O)` for the last board move

It also shows:
- move number
- side to move
- capture counts
- ko status
- last move
- move log

If the last move was pass or resignation, no board point is parenthesized.

## Recommended Codex Usage

For a session that is actually playing a game:

- use `play`, `pass`, and `resign` to change the game
- use `show` when structured state is needed
- use `chain` and `legal` for mechanical referee questions
- use `validate` if the session becomes unsure whether state is still consistent
- look at `game.txt` for the board, not the script source

Recommended discipline:
- never update `game.txt` by hand
- do not infer legality from visual inspection alone when the tool can answer it directly
- treat the referee as the source of truth for captures, ko, and liberties

## Operating Discipline

For an actual Codex-vs-human game, use a consistent loop:

1. Start the game with:

```bash
python3 go_ref.py init
```

2. When White plays, record that move immediately with:

```bash
python3 go_ref.py play --color white --move C3
```

3. Before choosing Black's move:
- inspect `game.txt` for the board view
- use `python3 go_ref.py show` for structured state
- use `python3 go_ref.py chain --point ...` for chain/liberty questions
- use `python3 go_ref.py legal --color black --move ...` for legality checks

4. After choosing Black's move, record it through the referee:

```bash
python3 go_ref.py play --color black --move E5
```

5. If anything seems uncertain, run:

```bash
python3 go_ref.py validate
```

6. If a move must be rolled back, use `undo` rather than editing files directly:

```bash
python3 go_ref.py undo
```

The key rule is simple:
- move choice may come from Codex
- move legality and state transitions must come from the referee

## Examples

Start a game and play two moves:

```bash
python3 go_ref.py init
python3 go_ref.py play --color black --move E5
python3 go_ref.py play --color white --move C3
```

Check whether `D4` is legal for Black:

```bash
python3 go_ref.py legal --color black --move D4
```

Inspect a chain:

```bash
python3 go_ref.py chain --point E5
```

End the game by passing:

```bash
python3 go_ref.py pass --color black
python3 go_ref.py pass --color white
```
