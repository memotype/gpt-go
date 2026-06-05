# Init prompt

Let's play a 9x9 game of Go. I play White and you play Black.

Before doing anything else:

1. Read `README.md` and treat it as the operating manual for this repo.
2. Use the referee CLI as the source of truth for legality, captures, ko,
   chains, liberties, move history, and board state.
3. Never manage board state by hand.
4. Never edit `game.txt` directly.

## Mission

Your job is to try to win the game.

You should:
- make your own strategic and tactical judgments
- investigate candidate moves before playing them
- use `query`, `try`, and `branch` proactively when useful
- use deeper branch analysis when the position is sharp
- avoid premature resignation

You should not:
- play the first legal move that comes to mind
- use `legal` as a move picker
- rely on visual inspection of `game.txt` alone when the referee can answer the
  question directly
- resign just because a group looks dead without serious tactical reading

## Ruleset

We are playing under Japanese rules with 6.5 komi.

The referee CLI is the authority on:
- legal moves
- captures
- ko
- passes and resignation
- move history
- board state

The referee is not an engine and does not choose moves for you.

## Interaction Model

We will communicate in short chat messages while the CLI manages the game.

If I enter an illegal White move:
- do not record it
- do not play a Black response
- briefly tell me the move is illegal and why
- ask for another White move

After you play a Black move:
- stop
- report the move clearly
- ask for my White move

Keep user-facing communication brief. Do not print large state dumps unless
needed.

## Working Discipline

Canonical play:
- use canonical commands for the real game
- record White's move immediately when I provide it
- choose Black's move only after inspecting the updated position

Short tactical reading:
- use `try play` and `try sequence`

Deeper tactical reading:
- create a branch and analyze there with `--branch <name>`

Never confuse branch outcomes with the canonical game state.

## Move Selection Guidance

Before every serious Black move:

- inspect the canonical position with `show` or `query board`
- consider serious candidate moves when the position is nontrivial
- use tactical tools to investigate uncertain candidates
- use a branch if one short hypothetical read is not enough
- reject moves that fail tactically
- choose your move only after enough analysis to justify it

## Branch Usage

Create a branch when:
- the line is too deep for one short hypothetical read
- multiple continuations need to be compared
- you want to preserve a hypothetical line for further reading
- the consequences of a move remain unclear after short tactical checks

Use branches as persisted analysis workspaces:
- `branch create --name <name>`
- `play --branch <name> ...`
- `query --branch <name> ...`
- `try --branch <name> ...`
- `undo --branch <name>`
- `branch reset ...` or `branch delete ...` when done

## Resignation And Endgame

Do not resign casually.

Only resign after serious analysis when the position is clearly lost.

If a group is claimed dead or the game reaches a scoring dispute:
- use verified facts from the CLI
- read out tactical continuations when needed
- distinguish what is verified from what is inferred
- do not pretend the referee has made a life-and-death or scoring ruling when
  it has not

## Communication Style

- Be brief.
- Report Black moves clearly.
- Ask for White's move in coordinate form such as `C3`.
- If White's move is illegal, explain briefly and ask for another move.
- Do not provide long strategic essays unless explicitly asked.

## Session Start

When beginning a new game:

1. Initialize the canonical game with the referee.
2. Inspect the starting state.
3. Choose and record Black's first move through the CLI.
4. Report the move and ask for White's reply.
