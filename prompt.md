# Game Prompt

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

After you have decided on and submitted a final Black move via the referee:
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
- on 9x9, do not treat ordinary-looking moves as routine
- assume each Black move needs a short adversarial read unless it is clearly
  forced, a pass, or a resignation
- consider serious candidate moves unless the move is clearly forced
- use tactical tools to investigate uncertain candidates
- use a branch if one short hypothetical read is not enough
- treat liberty count, connection, and legality as evidence, not proof that a
  move is good
- if White ignores a candidate, check what Black concretely gains
- if White answers with the strongest obvious reply, check what Black still has
- before reinforcing a group, prove the move does more than add connected
  stones
- reject moves that fail tactically
- choose your move only after enough analysis to justify it

When the local position is sharp:

- do not trust a candidate just because one short line looks good
- read at least the two strongest obvious White replies to a tightening move
- if White just played a small-looking move, re-check the whole-board urgency
  before answering locally
- prefer moves that keep multiple forcing follow-ups over moves that only take
  one liberty or make shape look tidy
- if more than one forcing continuation still looks plausible after short reads,
  switch to a branch before playing the real move

Mandatory adversarial read for each serious candidate:

1. State the candidate's intended purpose.
2. Use `try play` or `try sequence` to verify its immediate consequences.
3. Choose at least one strong White reply that tries to refute it.
4. Read at least one Black continuation after that reply.
5. Reject the candidate if the adversarial line leaves Black with no concrete
   gain or plausible continuation.

If the candidate mainly reinforces, connects, cleans up shape, or increases
liberties, this adversarial read is mandatory.

If one short sequence is not enough to understand the result, create a branch
and continue reading there before playing the canonical move.

Final blunder check before recording Black's move:

- What is White's strongest obvious reply?
- If White ignores the move, what did Black concretely gain?
- If the move mainly reinforces or connects, did it do more than add mass?
- Was the move tested with `try` or branch reading unless it is clearly forced,
  a pass, or a resignation?

Do not record the move until it passes this check.

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

This file is intended to be the single copy-pasteable prompt for starting a
new session.
