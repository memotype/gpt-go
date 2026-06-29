# Scratch / Working Plan

`ISSUES.md` is the authoritative findings log. This file is working memory for
the current implementation order, current decisions, and remaining work.

The current release line is `0.1.9`.

## Current State

Stage one is complete for:

- `ISSUE-001`
- `ISSUE-002`
- `ISSUE-003`
- `ISSUE-004`
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

The current player-doc set now includes:

- live-play governance in `docs/agents/player/gameplay-governance.md`
- a thin live session prompt in `docs/agents/player/session-prompt.md`
- a post-game review rubric in `docs/agents/player/evaluation-rubric.md`
- a thin post-game review prompt in `docs/agents/player/review-prompt.md`

## Active Priorities

No open maintainability issues remain in `ISSUES.md` right now. The current
priority is to keep the released command, metadata, and documentation contract
stable while future work is scoped.

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

No remaining queued issues. Keep the current contract stable in future work:

- shared query parser and dispatch changes should stay centralized
- governance docs should stay principle-oriented and defer syntax details to
  `docs/reference/cli.md`

## Validation Rules

Run after each meaningful code change set:

- `python3 -m unittest discover -s tests -v`
- `basedpyright`

Run when rendering or state-transition behavior changes:

- `python3 go_ref.py game validate`

Run when Markdown changes:

- `npm run lint:md`
