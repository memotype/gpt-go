# Issues Tracker

This file tracks maintainability, contract, and boundary issues that should be
addressed over time. Update `Status` as work progresses.

Allowed statuses:

- `open`
- `in_progress`
- `resolved`
- `wontfix`

Severity levels:

- `high`
- `medium`
- `low`

## ISSUE-001

- `Status`: `open`
- `Severity`: `high`
- `Area`: CLI contract / maintenance commands
- `Summary`: `validate` and `render` currently blur the meaning of
  `mutated: false` and the repo's non-mutating contract.
- `Why it matters`: The current contract distinguishes mutating commands from
  non-mutating ones, but these commands can still rewrite generated output and
  session metadata. That makes the JSON contract harder to trust and weakens
  the boundary between inspection commands and maintenance commands.
- `Evidence`:
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:569) `validate_command()`
    returns `mutated: False` but calls `render_target()` and, for sessions,
    `touch_session_meta()`.
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:578) `render_command()` returns
    `mutated: False` but also writes rendered output and may touch session
    metadata.
  - [docs/agents/coder/project-guidance.md](/home/isaac/dev/go/docs/agents/coder/project-guidance.md:12)
    says mutating commands refresh rendered output and `show`, `legal`,
    `chain`, and `query` must not mutate stored state or rendered output.
- `Recommended change`: Tighten the contract explicitly for maintenance
  commands and choose one policy:
  - either `validate` and `render` are maintenance mutations and must report
    `mutated: true`
  - or `validate` becomes fully read-only and `render` is the only explicit
    generated-output rewrite path

## ISSUE-002

- `Status`: `open`
- `Severity`: `medium`
- `Area`: Player governance / documentation boundaries
- `Summary`: The player governance doc currently carries concrete CLI/tooling
  surface details that should live only in the canonical CLI reference.
- `Why it matters`: Repeating concrete flags and payload details across docs
  increases drift risk and weakens the intended vertical boundary between
  strategy guidance and tool-contract documentation.
- `Evidence`:
  - [docs/agents/README.md](/home/isaac/dev/go/docs/agents/README.md:11) says
    shared tool behavior and CLI contracts live in the CLI reference.
  - [docs/agents/player/gameplay-governance.md](/home/isaac/dev/go/docs/agents/player/gameplay-governance.md:604)
    contains an appendix naming concrete implemented flags and payload fields.
  - [docs/reference/cli.md](/home/isaac/dev/go/docs/reference/cli.md:247)
    already documents the same query surfaces canonically.
- `Recommended change`: Keep governance principle-focused, replace detailed
  tool-surface listings with short references to the CLI doc, and leave only
  strategic boundary language in governance.

## ISSUE-003

- `Status`: `open`
- `Severity`: `medium`
- `Area`: CLI parser / command dispatch
- `Summary`: `game` and `session` query parser setup and command dispatch are
  heavily duplicated.
- `Why it matters`: The duplication raises drift risk when flags, payload
  options, or command routing change, especially for shared query behavior.
- `Evidence`:
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:337) through
    [go_ref.py](/home/isaac/dev/go/go_ref.py:428) duplicate parser setup for
    `game query` and `session query`.
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:740) through
    [go_ref.py](/home/isaac/dev/go/go_ref.py:876) duplicate query dispatch and
    argument plumbing across `game` and `session`.
- `Recommended change`: Introduce shared helpers for query parser registration
  and query command execution. If that still leaves too much branching, move to
  a small command table per target without changing CLI behavior.

## ISSUE-004

- `Status`: `open`
- `Severity`: `medium`
- `Area`: Referee utility / snapshot restoration
- `Summary`: `restore_snapshot()` hardcodes `komi` and `handicap` instead of
  preserving configuration from the source state.
- `Why it matters`: Hidden literal assumptions in shared restore utilities can
  silently break future config changes and make undo, replay, and last-event
  helpers less robust than they appear.
- `Evidence`:
  - [referee.py](/home/isaac/dev/go/referee.py:392) reconstructs state with
    literal `komi=6.5` and `handicap=0`.
- `Recommended change`: Preserve config from the source state or snapshot path
  rather than literals, and keep snapshot/restore utilities config-agnostic.

## ISSUE-005

- `Status`: `open`
- `Severity`: `medium`
- `Area`: Session metadata semantics
- `Summary`: Session `updated_at` is currently touched by maintenance-style
  commands as well as gameplay mutations, so its meaning is too broad.
- `Why it matters`: If `updated_at` does not clearly mean either session-state
  change, artifact refresh, or any command touch, it becomes hard to reason
  about and hard to test meaningfully.
- `Evidence`:
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:245) `touch_session_meta()`
    updates `updated_at`.
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:573) and
    [go_ref.py](/home/isaac/dev/go/go_ref.py:581) show it being called from
    `validate_command()` and `render_command()`, not just gameplay mutations.
  - [tests/test_go_ref.py](/home/isaac/dev/go/tests/test_go_ref.py:959)
    currently verifies timestamp monotonicity, not semantic intent.
- `Recommended change`: Define whether `updated_at` means session-state change,
  session-artifact change, or any command touch, then align command behavior
  and tests to that definition.
