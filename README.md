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
- a generated board view for humans

The tool does not provide:
- move recommendations
- strategy
- candidate ranking
- life/death judgment
- ladder reading
- territory or score estimation during play

## Files

- `state.json`
  - Authoritative game state and the primary machine-readable interface.

- `game.txt`
  - Generated board view for human inspection.
  - Do not use this as the machine interface.

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

2. Inspect the current state:

```bash
python3 go_ref.py show
```

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

After a legal move, the tool updates the stored state and refreshes the rendered board view.

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

Use this to refresh the rendered board view without changing state.

### `undo`

Undo the most recent move:

```bash
python3 go_ref.py undo
```

Undo multiple moves:

```bash
python3 go_ref.py undo --count 2
```

This rewinds state and refreshes the rendered board view.

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

## Recommended Codex Usage

For a session that is actually playing a game:

- use `play`, `pass`, and `resign` to change the game
- use `show` when structured state is needed
- use `chain` and `legal` for mechanical referee questions
- use `validate` if the session becomes unsure whether state is still consistent

Recommended discipline:
- never update generated output such as `game.txt` by hand
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
- use `python3 go_ref.py show` for structured state
- use `python3 go_ref.py chain --point ...` for chain/liberty questions
- use `python3 go_ref.py legal --color black --move ...` for legality checks

4. Choose Black's move

See the "Move Choice Discipline" section below.

5. After choosing Black's move, record it through the referee:

```bash
python3 go_ref.py play --color black --move E5
```

6. If anything seems uncertain, run:

```bash
python3 go_ref.py validate
```

7. If a move must be rolled back, use `undo` rather than editing files directly:

```bash
python3 go_ref.py undo
```

The key rule is simple:
- move choice must come from Codex
- move legality and state transitions must come from the referee

## Move Choice Discipline

The referee answers mechanical questions. It does not choose moves. Before
playing Black's move, Codex must choose deliberately.

After recording White's move and before playing Black's reply:

1. Use `show` to inspect the current board state.
2. Identify Black's most urgent problem in one sentence.
3. Identify 1-3 urgent White threats or Black weaknesses.
4. Identify 2-3 plausible Black candidate moves, unless there is only one
   clearly forcing move.
5. For each serious candidate, read the most obvious White reply.
6. Use referee commands only for mechanical questions:
   - `show` for exact state
   - `chain --point ...` for chains and liberties
   - `legal --color black --move ...` for legality
7. Reject any candidate that is immediately refuted by the obvious White reply.
8. Play the candidate that best preserves a plausible continuation.

Do not play the first legal move that comes to mind. Do not use `legal` as a
move generator and then pick from the list casually. Legal does not mean good.

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
