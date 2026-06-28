# Scratch / Working Plan

`ISSUES.md` is the authoritative findings log. This file is working memory for
the current implementation order, current decisions, and remaining work.

## Current State

Stage one is complete for:

- `ISSUE-001`
- `ISSUE-005`

The current command and metadata contract is:

- `validate` is read-only validation
- `render` is the explicit generated-output refresh command
- `result.mutated` means authoritative state mutation
- session `updated_at` advances for meaningful session state or persisted
  session-metadata changes, not for read-only inspection or render refresh

The current validation status is:

- `python3 -m unittest discover -s tests -v` passes
- `basedpyright` passes
- `python3 go_ref.py game validate` passes
- `npm run lint:md` passes

## Active Priorities

Recommended execution order from here:

1. `ISSUE-004`
2. `ISSUE-003`
3. `ISSUE-002`

Why this order:

- `ISSUE-004` is a focused utility-layer correctness fix and benefits from the
  newly stable stage-one contract.
- `ISSUE-003` is a structural refactor and should preserve the stage-one
  command semantics.
- `ISSUE-002` is documentation boundary cleanup and should describe the final
  tool and contract state after code refactors settle.

## Current Decisions

These decisions are active unless a later plan changes them deliberately:

- `state.json` remains authoritative
- `game.txt` remains generated output
- tooling remains informative-only
- stdout remains machine-readable JSON
- same-target CLI commands remain serialized
- governance docs stay principle-oriented
- executable tests cover contracts; prose wording does not

## Remaining Issue Plan

### ISSUE-004: snapshot restoration config handling

Current goal:

- make snapshot restoration preserve non-board configuration explicitly instead
  of relying on literals

Current attack:

- inspect `snapshot_state()` and `restore_snapshot()` together
- preserve `komi`, `handicap`, and any other required config in the snapshot /
  restore flow
- add focused tests for undo / restore with non-default configuration

### ISSUE-003: duplicated query parser and dispatch logic

Current goal:

- reduce duplicated `game` / `session` query plumbing without changing CLI
  behavior

Current attack:

- extract shared parser registration for the query subcommands
- extract shared query-dispatch plumbing for common flags and routing
- preserve JSON shape, CLI names, and locking behavior exactly

### ISSUE-002: governance doc boundary cleanup

Current goal:

- move concrete tool-surface detail back under the CLI reference and keep
  governance focused on judgment and tool boundaries

Current attack:

- trim concrete query-flag and payload-shape detail from player governance
- replace repeated tool-surface detail with references to
  `docs/reference/cli.md`
- keep the informative-only boundary language intact

## Validation Rules

Run after each meaningful code change set:

- `python3 -m unittest discover -s tests -v`
- `basedpyright`

Run when rendering or state-transition behavior changes:

- `python3 go_ref.py game validate`

Run when Markdown changes:

- `npm run lint:md`
