# Go Referee CLI

This repo provides a 9x9 Go referee and tactical inspection toolkit for Codex.
Its purpose is not merely to keep play legal. Its purpose is to help Codex play
competitive Go, reason tactically, and try to win while delegating verified
mechanics to deterministic tools.

## Competitive Intent

Codex is expected to:
- try to win the game
- choose moves deliberately rather than casually
- investigate candidate moves before playing them
- use deeper branch analysis when the position is sharp
- avoid premature resignation

Codex is not expected to:
- hand-manage the board
- edit `game.txt` directly
- use `legal` as a move picker
- confuse tactical inference with referee-verified fact

## What The Tool Does

The CLI manages:
- board state
- legal move checking
- captures
- connected chains and liberties
- simple ko
- pass and resignation
- undo
- tactical board queries
- hypothetical move and sequence simulation
- persisted hypothetical branches
- a generated board view for humans

The CLI does not provide:
- move recommendations
- strategy
- candidate ranking
- automatic life/death judgment
- automatic scoring judgment
- ladder reading beyond what Codex can inspect with queries and variations

The referee is the source of truth for mechanics, not for strategy. Codex
should make strategic and tactical judgments itself, then use the CLI to verify
facts and read out concrete lines.

## Analysis Modes

The repo supports three analysis modes:

1. Canonical game state
   - The real game lives in `state.json` and `game.txt`.
2. Stateless tactical reading
   - `try` reads out hypothetical moves and short sequences without mutating any
     files.
3. Persisted deeper reading
   - `branch` creates named hypothetical workspaces under
     `analysis/branches/`.

Use the lightest tool that answers the question:
- use canonical state for real play
- use `try` for short tactical reads
- use `branch` when the line is deep, contested, or worth preserving

## Files

- `state.json`
  - Authoritative canonical game state and the primary machine-readable
    interface.

- `game.txt`
  - Generated board view for human inspection.
  - Do not use this as the machine interface.
  - Do not edit it directly.

- `analysis/branches/<branch_name>/state.json`
  - Authoritative state for one persisted hypothetical branch.

- `analysis/branches/<branch_name>/game.txt`
  - Rendered board view for one persisted hypothetical branch.

Treat `state.json` as the live truth and `game.txt` as a rendered view.
Persisted hypothetical analysis lives under `analysis/branches/` and never
changes the canonical game unless you explicitly use canonical commands.

## Starting A Game

Initialize a fresh 9x9 game:

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

### `init`

Create a fresh canonical game state and render the initial board.

```bash
python3 go_ref.py init
```

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

After a legal move, the tool updates the stored state and refreshes the
rendered board view for that target.

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

Resign only after serious analysis. Do not resign casually because a group
“looks dead.”

### `legal`

List all legal board moves for a color:

```bash
python3 go_ref.py legal --color black
```

Check one specific move:

```bash
python3 go_ref.py legal --color black --move D5
```

This command is for mechanical legality only. It does not evaluate which legal
move is better.

### `chain`

Inspect the chain and liberties at a point:

```bash
python3 go_ref.py chain --point D4
```

Use this for simple liberty checks or capture confirmation. Use `query chain`
when you want richer tactical context.

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

Use `query` when Codex wants verified local facts such as:
- whether a point would be self-atari
- which chains are adjacent to a group
- which groups are currently in atari
- how an empty region is bordered
- which side is weak right now

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

Use `try` when Codex wants verified tactical consequences such as:
- what a move would capture
- what liberties the played chain would have
- whether a candidate line fails immediately
- whether a local exchange changes ko or atari status
- whether an apparently good move is actually refuted

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

Use `branch` when Codex wants to:
- preserve a variation longer than a quick `try sequence`
- compare multiple candidate continuations
- continue reading positions that need more than a short hypothetical check
- keep a running hypothetical board state without touching the real game

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

Use this to refresh a rendered board view without changing state.

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

- stdout:
  - JSON only

- stderr:
  - human-readable diagnostics

- exit code:
  - `0` on success
  - nonzero on failure

Codex should read stdout for structured results and use stderr only for brief
failure context.

## Documentation Hygiene

If you touch Markdown documentation in this repo, run:

```bash
npm run lint:md
```

before considering the change complete.

## Tool Selection Playbook

Use the tools intentionally:

- “What is weak right now?” → `query board`
- “How many liberties does this group have?” → `chain` or `query chain`
- “Is this cut or connection tactically sound?” → `query point` + `try play`
- “What happens in the next 2-5 forcing moves?” → `try sequence`
- “I need to preserve or compare longer lines” → `branch create` + branch-targeted
  `play`, `query`, `try`, `undo`
- “Can I back up inside analysis?” → `undo --branch`
- “I need canonical truth before committing” → canonical `show`, `query`,
  `validate`

Anti-patterns:
- do not use `legal` as a move picker
- do not rely on `game.txt` visual inspection alone
- do not treat one short line as conclusive if the position still feels unclear
- do not conflate branch outcomes with the canonical game state

## Recommended Codex Usage

For a session that is actually playing a game:
- use `play`, `pass`, and `resign` to change the real game
- use `show`, `query`, and `chain` for verified state
- use `try` for short tactical verification
- use `branch` when deeper reading is needed
- use `validate` if state consistency is ever in doubt

Recommended discipline:
- never update generated output such as `game.txt` by hand
- do not infer legality from visual inspection alone when the tool can answer
  it directly
- treat the referee as the source of truth for captures, ko, liberties, move
  history, and hypothetical outcomes returned by `try`
- treat tactical or strategic conclusions as Codex inference unless both
  players agree on them
- treat branches as analysis workspaces, not as the canonical game

## Operating Discipline

For actual Codex-vs-human play, use this loop:

1. Initialize the game:

```bash
python3 go_ref.py init
```

2. When White plays, record that move immediately:

```bash
python3 go_ref.py play --color white --move C3
```

3. Before choosing Black's move, inspect the position using canonical tools.
4. Choose Black's move deliberately.
5. Record Black's move through the referee:

```bash
python3 go_ref.py play --color black --move E5
```

6. If anything seems uncertain, run:

```bash
python3 go_ref.py validate
```

7. If a move must be rolled back, use `undo` rather than editing files.

The key rule is simple:
- move choice must come from Codex
- move legality, board facts, and state transitions must come from the referee

## Move Selection Guidance

Before every serious Black move, Codex should analyze enough to justify the
move it chooses.

A good default loop is:

1. Inspect the canonical position with `show` or `query board`.
2. Consider the most serious problems or opportunities in the position.
3. When the position is nontrivial, compare more than one serious move.
4. Use the tools that fit the question:
   - `query point` for local tactical facts
   - `query chain` for group status and neighboring pressure
   - `try play` for one-move consequences
   - `try sequence` for short forcing lines
5. If short tactical checks are not enough, continue reading in a branch.
6. Reject moves that fail tactically.
7. Play the move you judge strongest after analysis.

Do not play the first legal move that comes to mind, but do not treat this as
an inflexible script either.

## Branch Usage

Create or extend a branch when:
- one short `try sequence` is not enough
- multiple continuations need to be compared
- you want to preserve a hypothetical line for further reading
- the consequences of a move remain unclear after short tactical checks

Recommended branch pattern:
1. Create a branch from canonical or from another branch.
2. Use `play`, `pass`, `query`, `try`, `undo`, and `show` with
   `--branch <name>`.
3. Reset or delete the branch when it is no longer useful.

Safety rules:
- branch commands never mutate canonical `state.json` or `game.txt`
- canonical commands never mutate branch files
- branch judgments are still inference unless backed by verified mechanics and
  player agreement

## Reasoning Discipline

Codex should distinguish four kinds of statements:

- `verified`: directly supported by CLI output
- `inferred`: tactical or strategic judgment made by Codex
- `agreed`: accepted by both players
- `contested`: unresolved claims about life, death, or scoring

Examples:
- `verified`: “This chain has 2 liberties.”
- `inferred`: “White can likely kill this group if White plays first.”
- `agreed`: “Both players agree this corner group is dead.”
- `contested`: “White claims the center Black stones are dead, but Black
  disputes it.”

The referee does not make judgments, but it provides enough facts for Codex to
do so responsibly.

## Resignation And Endgame Discipline

Do not resign because a group merely looks dead.

Before resigning or conceding a major group:
- verify the relevant tactical facts with `query`
- read short forcing lines with `try sequence`
- use a branch for deeper kill/save continuations if the line is nontrivial

If the game reaches scoring or life-and-death discussion:
- use verified mechanics plus Codex judgment
- clearly separate contested claims from agreed outcomes
- do not pretend the referee has made a scoring or life/death ruling when it
  has not

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

Inspect a chain with neighboring groups:

```bash
python3 go_ref.py query chain --point E5
```

Use `query board` before choosing a move:

```bash
python3 go_ref.py query board
```

Test whether a candidate move holds tactically:

```bash
python3 go_ref.py try play --color black --move D4
```

Reject a candidate after reading a short line:

```bash
python3 go_ref.py try sequence --moves "B:D4,W:C4,B:E4"
```

Create a persisted branch and inspect it:

```bash
python3 go_ref.py branch create --name center-fight
python3 go_ref.py play --branch center-fight --color black --move D4
python3 go_ref.py play --branch center-fight --color white --move C4
python3 go_ref.py query board --branch center-fight
python3 go_ref.py undo --branch center-fight
```

Reset or delete a branch after analysis:

```bash
python3 go_ref.py branch reset --name center-fight --from canonical
python3 go_ref.py branch delete --name center-fight
```

Refuse premature resignation and read deeper first:

```bash
python3 go_ref.py branch create --name kill-check
python3 go_ref.py try sequence --branch kill-check --moves "B:E4,W:D4,B:F4"
```

End the game by passing:

```bash
python3 go_ref.py pass --color black
python3 go_ref.py pass --color white
```
