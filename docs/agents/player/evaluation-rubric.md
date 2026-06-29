# Player Evaluation Rubric

Use this rubric to review a completed 9x9 game after play is over.

This document is for post-game analysis, not live move selection. Its purpose
is to identify recurring judgment patterns and turn them into better player
governance over time.

Prefer reviewing behavior patterns over move-by-move nitpicking alone. A weak
move matters, but the more useful question is usually what kind of thinking
made that move likely.

## When To Use This

Use this rubric when:

- a game has ended or reached a review pause
- you want to identify Black's recurring strengths and mistakes
- you want to suggest updates to player guidance
- you want to compare whether governance changes are improving play over time

Do not use this rubric as a live move-selection checklist during play. The live
operating rules belong in `docs/agents/player/gameplay-governance.md`.

## Review Dimensions

### Urgency Judgment

Ask whether Black correctly identified which moves were truly `forced` and
which only looked locally urgent.

Good signs:

- Black answered real captures, ataris, ko threats, or decisive cuts promptly
- Black tenukied when the local issue was only `contestable` or `open`
- Black did not let the last exchange inherit urgency automatically

Warning signs:

- Black kept replying nearby without naming the concrete gain White would get
  if Black played elsewhere
- Black treated local contact, recent liberties, or unfinished shape as
  urgency by default

### Whole-Board Resets

Ask whether Black reset the board picture once a local fight cooled down.

Good signs:

- Black compared the best local continuation against a whole-board alternative
- Black stopped following a stale local story once no forcing line remained
- Black found a larger point on the opposite or orthogonal side when the last
  move was not decisive

Warning signs:

- Black stayed tactically adjacent to the action by habit
- Black continued the same local plan without re-earning its urgency
- Black treated “this is where the last move was” as a reason to play nearby

### Life And Settling

Ask whether Black improved the actual condition of its groups, not merely their
 short-term survival.

Good signs:

- Black made a base
- Black expanded eye space
- Black connected to independently healthy stones
- Black turned a weak group into a realistically settled one

Warning signs:

- Black made groups “not dead yet” without making them meaningfully safer
- Black kept adding stones to a heavy group without creating a credible life
  plan
- Black filled points it might later need for eye space or outward growth

### Profit And Territory

Ask whether Black converted strength, sente, or pressure into concrete gain.

Good signs:

- Black secured a durable territorial boundary
- Black used thickness to claim outside profit
- Black attacked in a way that produced territory, shape damage, or sente
- Black took a large open point when no tactical sequence demanded otherwise

Warning signs:

- Black kept attacking without gaining profit
- Black defended in a way that only preserved contact
- Black played moves that neither secured territory nor built future profit

### Candidate Breadth And Role Comparison

Ask whether Black compared distinct move roles or just shuffled among nearby
maintenance ideas.

Good signs:

- Black compared local defense, attack, profit, base-making, and whole-board
  alternatives
- Non-forcing turns included at least one candidate not adjacent to the same
  focal chain
- Black rejected the first natural local move when it proved hollow

Warning signs:

- all candidates were adjacent to the same local story
- Black jumped from “that local move is bad” to “so I should play another move
  next to it”
- Black compared shape tidying moves without asking what any of them built

### Attack Quality

Ask whether Black's attacks produced burden, profit, or initiative rather than
one-ply severity.

Good signs:

- the attack made White heavier, lower, or more overconcentrated
- the attack built outside strength or profit for Black
- the attack forced a concession that mattered later

Warning signs:

- Black played slow ataris that White could answer comfortably
- Black attacked only to continue local contact
- the attack did not change White's strategic burden

### Anti-Pattern Frequency

Note how often these showed up:

- tactically adjacent tunnel vision
- empty reinforcement
- slow atari
- self-filling safe shape
- “one more move here” continuation
- failure to abandon a stale local story
- defending stones that became “not dead yet” but not settled

The goal is not perfect counting. The goal is to detect which bad habits
dominate the game.

### Good Exceptions

Note strong moments too, especially when Black:

- made a good whole-board tenuki
- recognized a real tactical threat correctly
- attacked for profit rather than noise
- made a base or improved eye space at the right time
- secured a durable territorial boundary
- reset properly after a fight cooled down

## Common Failure Modes

The most important thing to diagnose is not only which move was bad, but which
thinking pattern repeated.

Common failure modes include:

- Black over-valued moves that were tactically adjacent to the action
- Black confused “recent” with “urgent”
- Black kept a local story alive after its forcing value was gone
- Black defended chains that were already safe enough while ignoring bigger
  opportunities
- Black attacked without cashing out territory, outside strength, or sente
- Black preserved shape for one more turn without building life or base

When possible, name the first move where the drift began rather than only the
worst move after the drift was already obvious.

## Good Signs

Strong games usually show some combination of:

- correct identification of truly forced replies
- willingness to tenuki when the board does not justify another local move
- moves that improve life, base, eye space, or settlement
- attacks that create profit or strategic burden
- resets that reopen the whole board after local urgency expires
- abandonment of failed local plans instead of repeated small repairs

## Review Template

Use this template when summarizing a game:

- Best Black move:
- Worst Black move:
- First move where Black drifted into local inertia:
- Number of non-forcing turns where Black failed to compare a whole-board alternative:
- Number of moves that clearly improved life, base, territory, or attack profit:
- Main recurring failure mode:
- Main positive pattern:
- Governance lesson suggested by this game:

Keep the summary concrete. Name the move numbers, the board consequences, and
the recurring thought pattern that best explains the result.
