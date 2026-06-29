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
- after two consecutive passes, treat the game as in scoring rather than
  irreversibly over
- if play must continue after a pass dispute, use `game resume` instead of
  undoing the passes

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

If a session reaches scoring after two passes, use `session resume` to keep
reading or `session finalize` to close that hypothetical line without erasing
the passes.

## Recommended Analysis Pattern

Use `session` to think before you commit, but do not turn analysis into a
ritual. The important ground rules are:

1. Record White's real move immediately on `game`.
2. Inspect the updated canonical position with `game query board`.

After that, let the position determine the reading.

Candidate generation is creative. Candidate approval is adversarial.

Treat every candidate as guilty until proven useful. Try to falsify the move
before you deepen it. Do not let a move survive just because it is legal,
active-looking, connected, or adjacent to the current local story.

In general:

1. classify the local issue
2. generate a few distinct candidate roles
3. run a shallow factual rejection pass
4. deepen only the candidates that survive and still lead to a forcing line
5. run a final critic pass before recording the move on `game`

This is not a move-selection algorithm. The point is to keep real play and
hypothetical reading separate while giving Codex room to judge shape, life,
efficiency, and whole-board tradeoffs.

## Urgency Classification

Before treating a nearby local issue as mandatory, classify it:

- `forced`
  - White has an immediate capture, atari, ko, decisive cut, forced
    connection, or similarly concrete tactical consequence if Black tenukis
- `contestable`
  - White can improve locally, but cannot force a decisive result immediately
- `open`
  - there is no immediate local sequence requiring a reply

Only `forced` issues should consume the turn by default.

When a local line becomes `contestable` or `open`, stop treating that area as
the default plan and compare at least one candidate outside the current local
cluster.

When White has made a thin, heavy, overcommitted, or low-value local shape and
Black is not under immediate tactical collapse, compare attacking
continuations that press on that burden rather than defaulting to another
maintenance move.

If a local read shows White can still capture or force the same bad outcome
after White's strongest obvious reply, mark that plan or group as `failed` or
effectively dead rather than treating it as still unsettled.

Once a plan or group is marked `failed`, stop defaulting to moves adjacent to
it unless a new line creates a different concrete endpoint such as capture,
escape, outside connection, ko, or boundary.

## Role-Based Candidate Discipline

Use breadth first as a rejection tool, not as a ritualized search tree.

## Candidate Breadth Before Tactical Depth

When the move is nontrivial, do not jump directly from "that move is bad" to
"therefore I should add another stone nearby."

Instead, consider a small set of distinct candidate roles such as:

- urgent defense or capture
- forcing attack
- pressing from strength to keep White sealed in or low
- move that makes White heavy while Black stays light
- connection or escape
- move that preserves sente by attacking profitably instead of defending
  passively
- move elsewhere that takes profit or initiative from the opponent's local commitment
- quiet move that secures a concrete result

If no chain is currently in atari and no immediate capture, ko, or forcing cut
has been identified, include at least one candidate that is not adjacent to the
same focal Black chain. This candidate may still relate to the same side of the
board, but it should test outward development, counterplay, or whole-board
timing rather than another nearby maintenance move.

This does not require a fixed number of candidates every turn. Use it when
Black is in danger of drifting into one-track local play without comparing a
different kind of idea.

A short first pass should kill obviously bad ideas early so only credible
candidates receive deeper tactical reading.

## Shallow Factual Rejection

Before trusting a candidate, perform a cheap falsification pass in `session`:

- state the move's concrete purpose in one sentence
- inspect the resulting Black chain if the move touches, extends, connects to,
  or creates a local fight
- inspect the affected White chain if the move claims to attack, squeeze, or
  reduce it to forcing pressure
- compare the result against White's strongest obvious local reply

If the move fails this first pass, reject it instead of reading deeper.

Before trusting a sharp local move, read White's strongest obvious local reply
first.

Do not treat a move as urgent or good merely because it:

- reduces an enemy chain's liberties
- creates an atari threat that White can answer comfortably
- looks active or severe for one ply
- is adjacent to the same weak group as the previous candidate
- preserves a local liberty count without creating a credible endpoint

If Black's move only relocates liberties, creates a larger but still pressured
chain, or preserves the same race without a concrete gain, reject it or keep
reading only if the line remains truly forcing.

Do not confuse short-term severity with profit. A move that looks active for
one ply may still be poor if White's natural answer leaves Black heavy, thin,
forced low, or still unable to claim worthwhile outside development.

## Immediate Rejection Rules

Reject a candidate immediately if any of these are true, unless the move
captures, forces ko, or creates a clearly superior tactical result that can be
verified in the line:

- the move creates a new Black chain in atari
- the move claims to attack, but the attacked White chain is not left in atari
  or a concrete forcing shortage after White's strongest obvious reply
- the move claims to defend, but Black still faces the same forcing outcome
  after White's strongest obvious reply
- the move's purpose cannot be stated concretely and verified from session
  facts
- the move only preserves a local story, relocates liberties, or creates a
  bigger but still bad Black target

Also reject moves that:

- save the chain by crawling underneath, filling Black's own shape, or taking
  a point Black may later need for eye space or outward development
- make Black heavier or lower while a different defense keeps White unsettled
  or preserves outside strength
- win a local liberty-count comparison but hand White the more valuable
  follow-up, connection, or shaping point

## Post-Move Factual Audit

When a candidate touches, extends, connects to, or claims to defend a weak
Black chain, verify the resulting facts in `session` before trusting the move.

Name the exact threat the move is supposed to answer. Then inspect the
resulting chain after the move rather than assuming that adding a stone or
making a connection created safety.

If the candidate merges chains, inspect the merged chain itself. Do not assume
that connection equals safety just because the stones are now linked.

Reject the move as a successful defense if the post-move chain:

- is still in atari
- still faces the same forcing liberty shortage
- still fails to answer the named threat after White's strongest obvious reply

Do not approve a move merely because it changed liberty counts, relocated a
shortage, or made the local facts look tidier on one ply. Ask whether the move
changed the expected local outcome.

Before investing another move in a weak Black group, name the credible endpoint
the move is supposed to create, such as:

- capture something
- connect to independently safe stones
- escape into open space
- create stable internal space
- obtain a forcing trade worth the remaining danger

If no credible endpoint appears after concrete reading, reject repeated local
investment even if the move preserves the current liberty count or avoids an
ugly-looking shape for one turn.

If a concrete read shows that White can still capture after White's strongest
obvious reply, and Black's next move does not change that expected result,
stop describing the local plan as an ongoing defense. Treat it as failed until
you can name a different concrete endpoint.

When a candidate occupies a current liberty or eye-space point of an already
connected Black chain, treat it as suspect unless it does something concrete,
such as:

- gives atari or starts a real capture sequence
- prevents a named enemy escape, connection, or invasion
- creates an external route or expansion path for Black
- secures a specific territorial boundary
- resolves a forcing tactical problem

Reject inward or self-filling moves that only tidy liberties, preserve shape
for one turn, or continue a stale local story without producing one of those
concrete results. Be especially suspicious of second-line edge chases and "one
more move here" ideas after the surrounding read has already gone bad.

State the effect on both Black's chain and the affected White chain. If the
move only improves a local statistic without changing the expected result,
compare it against an outward or whole-board candidate.

This audit is not a universal liberty-threshold rule. The point is to check
whether the move actually changed the tactical problem rather than just moving
it around, and whether the move produced a group worth continuing to invest in.

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

A move is not validated by finding one friendly continuation. First compare it
against White's most obvious forcing exploitation of the candidate.

Do not count a move as a successful answer to atari or severe liberty pressure
merely because it connects to more stones. If the endangered Black chain, or
the larger chain it joins, still has only 1 liberty after the move, treat the
position as still forcing and keep reading.

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

If the forcing sequence ends without a capture, atari, ko, decisive cut,
forced connection, immediate escape, or similarly concrete result, stop
treating that area as the default plan. Return to the whole board and compare
at least one candidate that is not adjacent to the same focal Black chain.

Reject a candidate if the forced-line read shows Black remains under pressure
without getting enough in return.

If White's strongest obvious reply still captures, traps, or otherwise leaves
Black with the same failed outcome, stop treating further adjacent moves as
the default continuation. Mark that local plan as failed and compare at least
one candidate elsewhere before returning.

Continue until the local fight is actually stable, or until the candidate is
clearly worse than a quieter alternative.

Do not treat "the move changed something" as sufficient proof. The forcing read
must show a changed tactical or strategic outcome, not just a changed local
statistic.

For this rule, "concrete gain" is Codex's tactical judgment about the branch
result. It is not referee output and must not be inferred from the CLI as a
move recommendation or life-and-death judgment.

## Attacking Is Allowed

Black does not need a capture to justify pressure.

An attack is good if it produces a concrete result such as profit, outside
strength, initiative, or a heavier and less flexible White shape.

If White's stones are overconcentrated, under-supported, or overcommitted,
look for moves that worsen that burden rather than simply "staying safe."

An attack may still be good without a capture if White's natural reply leaves
White heavier, more sealed in, less connected, or more burdened than before.

Backing off is not automatically superior just because it looks calmer. If a
more forceful move keeps Black tactically sound while making White's position
harder to manage, that is a real point in its favor.

## Pre-Commit Critique

Before recording Black's final move on `game`, switch briefly from player mode
to critic mode.

Assume the preferred move is bad and give the strongest concrete critique of
it:

- what threat it fails to answer
- what gain it fails to create
- what useful point it needlessly fills
- whether it gives up initiative unnecessarily
- whether it defends in a smaller way than necessary
- whether it saves the stones in the most submissive available way
- whether a stronger attacking move would leave White with the harder long-term problem
- whether it relieves White's burden instead of increasing it
- what stronger opponent reply makes the move look hollow
- whether the move is only preserving a local fact that is no longer urgent

This critique should sound like post-game review, not advocacy. Analyze the
candidate as if it were the move that lost the game.

Do not justify a move with words like:

- solid
- thick
- safe
- calm
- efficient

unless you can name the exact tactical or positional change the move creates.

If the critique shows the move only looks legal, connected, thick, or safe
without producing a concrete gain after White's best reply, reject it and keep
reading or choose another candidate.

Apply the same rejection if another candidate also saves the group but does so
with better outside shape, more pressure on White, or less long-term burden.
Do not justify the heavier move merely because it survives on this turn.

When two candidates are both tactically acceptable, prefer the one that leaves
White with the more difficult strategic burden unless it creates a new forcing
defect in Black.

Apply the same rejection if the move "saves" stones by connecting them into a
larger group that still has just 1 liberty or is still under the same forcing
attack. That is not a resolved defense; it is just a bigger target.

## Global Reset After Material Change

After a material change, pause briefly and reset the whole-board picture before
continuing the previous plan by inertia.

Use this reset after events such as:

- a capture
- a major connection
- a failed tactical line
- ko
- a pass dispute or resumption
- a group becoming clearly dead or clearly alive

Keep the reset brief. Ask:

- what changed on the full board
- which chains are now weak
- which previous goals no longer matter
- whether a more urgent area now exists
- whether the old local fight has become `contestable` or `open` rather than
  `forced`

Before trusting a new candidate in or near the affected area, query the
relevant points or chains again and verify which stones still exist. Do not
keep describing threats, ataris, eyes, escapes, or connections that depended
on a chain that may already have been captured or removed.

If the reset shows that the old supporting chain is gone, or that the local
result is now fixed, forbid yourself from reasoning from the earlier shape by
inertia. Start from the refreshed board facts instead.

This is not a requirement to rescan the whole board after every move. It is a
guardrail against stale plans surviving after the position changed materially.

## Concrete Language Discipline

Positional judgment is allowed, but vague praise is not enough on its own.

Do not justify a move as:

- safe
- thick
- settled
- calm
- solid
- efficient

unless you can translate the claim into a concrete board consequence such as:

- a chain gains liberties
- a chain connects to an independently live group
- a forcing move is removed
- a territory boundary becomes secure
- an opponent loses an escape route
- an opponent is forced into a low shape
- an opponent becomes heavy
- Black gains initiative elsewhere
- Black builds outside strength while White takes only small local relief
- a capture threat becomes real

The purpose is not to ban positional language. The purpose is to make the
reasoning falsifiable against the board.

Do the same with urgency claims. Do not treat a local issue as urgent merely
because it is nearby, because it changed recent liberties, or because it feels
unfinished. Name the concrete result White obtains if Black plays elsewhere.
If you cannot name one, the issue is probably `contestable` or `open`, not
`forced`.

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

## Tooling Boundary

Use the referee only for factual state inspection, legality, captures, ko,
history, chains, liberties, rendering, and hypothetical reading support.
Concrete command syntax and payload details live in
[../../reference/cli.md](../../reference/cli.md).

When deciding whether a tool addition belongs here, keep the distinction sharp:

- good tooling improves external working memory with neutral factual evidence
- bad tooling smuggles strategic judgment into the referee

Keep the following out of the tool layer:

- move recommendations
- candidate rankings
- urgency rankings
- life-and-death verdicts
- territory judgment
- best-move summaries
- hidden strategic policy disguised as query output
