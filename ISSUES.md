# Issues Tracker

This file tracks maintainability, contract, and boundary issues that should be
addressed over time. Update `Status` as work progresses.

All tracked issues are currently resolved. This file remains the authoritative
maintainability log for future findings.

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

- `Status`: `resolved`
- `Severity`: `high`
- `Area`: CLI contract / maintenance commands
- `Summary`: The maintenance-command contract is explicit: `validate` is
  read-only, `render` refreshes generated board output, and `mutated` refers
  to authoritative state mutation.
- `Why it matters`: This keeps the JSON contract trustworthy and preserves a
  clean boundary between authoritative state mutation and generated-artifact
  refresh.
- `Evidence`:
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:569) `validate_command()` loads
    state, runs `validate_state()`, and returns JSON without calling
    `render_target()` or `touch_session_meta()`.
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:575) `render_command()` refreshes
    generated output without changing authoritative state.
  - [docs/reference/cli.md](/home/isaac/dev/go/docs/reference/cli.md:89)
    defines `validate` and `render` as maintenance commands and clarifies the
    contract.
  - [tests/test_go_ref.py](/home/isaac/dev/go/tests/test_go_ref.py:660),
    [tests/test_go_ref.py](/home/isaac/dev/go/tests/test_go_ref.py:693), and
    [tests/test_go_ref.py](/home/isaac/dev/go/tests/test_go_ref.py:707) cover
    the `mutated` field and non-mutation / artifact-refresh behavior.
- `Recommended change`: Keep this contract stable in later refactors. If a
  future command mixes validation with artifact refresh again, document it as a
  maintenance command explicitly and cover it with executable contract tests.

## ISSUE-002

- `Status`: `resolved`
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
    now keeps only principle-level tool-boundary guidance and points concrete
    syntax back to the CLI reference.
  - [docs/reference/cli.md](/home/isaac/dev/go/docs/reference/cli.md:247)
    already documents the same query surfaces canonically.
- `Recommended change`: Keep governance principle-focused, point concrete tool
  syntax and payloads back to the CLI reference, and leave only strategic
  boundary language in governance.

## ISSUE-003

- `Status`: `resolved`
- `Severity`: `medium`
- `Area`: CLI parser / command dispatch
- `Summary`: `game` and `session` query parser setup and command dispatch are
  heavily duplicated.
- `Why it matters`: The duplication raises drift risk when flags, payload
  options, or command routing change, especially for shared query behavior.
- `Evidence`:
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:358) and
    [go_ref.py](/home/isaac/dev/go/go_ref.py:403) now share query parser
    registration through `add_query_subcommands()`.
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:659) centralizes query dispatch
    and argument plumbing through `dispatch_query_command()`.
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:778) and
    [go_ref.py](/home/isaac/dev/go/go_ref.py:837) route both `game query` and
    `session query` through the same helper without changing CLI behavior.
- `Recommended change`: Keep shared query helpers as the single place for
  query parser and dispatch changes. If broader command duplication becomes a
  future problem, consider a small command table per target while preserving
  the existing JSON contract and locking behavior.

## ISSUE-004

- `Status`: `resolved`
- `Severity`: `medium`
- `Area`: Referee utility / snapshot restoration
- `Summary`: `restore_snapshot()` hardcodes `komi` and `handicap` instead of
  preserving configuration from the source state.
- `Why it matters`: Hidden literal assumptions in shared restore utilities can
  silently break future config changes and make undo, replay, and last-event
  helpers less robust than they appear.
- `Evidence`:
  - [referee.py](/home/isaac/dev/go/referee.py:346) threads live config into
    `restore_snapshot()` when reconstructing the pre-event state for
    `last_event_summary`.
  - [referee.py](/home/isaac/dev/go/referee.py:398) restores snapshots from
    explicit `schema_version`, `board_size`, `komi`, and `handicap` inputs
    instead of literals.
  - [referee.py](/home/isaac/dev/go/referee.py:1229) preserves the active
    game's config while replaying undo history through restored snapshots.
  - [tests/test_go_ref.py](/home/isaac/dev/go/tests/test_go_ref.py:251)
    verifies undo preserves non-default `komi` and `handicap`.
- `Recommended change`: Keep snapshot/restore helpers config-agnostic. If
  future configurable state is added, thread it through the same restore path
  rather than reintroducing literals.

## ISSUE-005

- `Status`: `resolved`
- `Severity`: `medium`
- `Area`: Session metadata semantics
- `Summary`: Session `updated_at` now advances for meaningful session state or
  persisted session-metadata changes, not for read-only inspection or render
  refresh.
- `Why it matters`: This gives the timestamp one clear meaning and makes the
  metadata behavior easier to reason about and test.
- `Evidence`:
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:245) `touch_session_meta()`
    updates `updated_at`.
  - [go_ref.py](/home/isaac/dev/go/go_ref.py:569) through
    [go_ref.py](/home/isaac/dev/go/go_ref.py:578) show that
    `validate_command()` and `render_command()` do not call
    `touch_session_meta()`.
  - [tests/test_go_ref.py](/home/isaac/dev/go/tests/test_go_ref.py:998)
    confirms mutation-driven timestamp advancement.
  - [tests/test_go_ref.py](/home/isaac/dev/go/tests/test_go_ref.py:1024) and
    [tests/test_go_ref.py](/home/isaac/dev/go/tests/test_go_ref.py:1067)
    cover read-only and render-refresh timestamp stability.
- `Recommended change`: Keep `updated_at` scoped to meaningful session or
  persisted session-metadata changes. If artifact timestamps become necessary
  later, add a separate field rather than widening `updated_at` again.
