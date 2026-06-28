# Scratch / Working Plan

`ISSUES.md` is the authoritative log of findings. This file is working memory
for turning those findings into concrete changes.

## Current Objective

Resolve the maintainability and contract issues tracked in:

- [ISSUES.md](./ISSUES.md)

Keep the work aligned with the repo's existing boundaries:

- `state.json` is authoritative
- `game.txt` is generated output
- keep tooling informative-only
- keep stdout machine-readable JSON
- preserve same-target serialization
- avoid brittle prose tests

## Execution Order

Recommended attack order:

1. `ISSUE-001` and `ISSUE-005`
2. `ISSUE-004`
3. `ISSUE-003`
4. `ISSUE-002`

Why this order:

- `ISSUE-001` and `ISSUE-005` define the command and metadata contracts that
  later refactors should preserve.
- `ISSUE-004` is a utility-layer correctness hardening change with limited
  surface area.
- `ISSUE-003` is a structural refactor and should happen after the contract
  decisions are fixed.
- `ISSUE-002` is documentation cleanup and should reflect the final code and
  contract state.

## Issue Attack Plan

### ISSUE-001: `validate` / `render` contract mismatch

Goal:

- Make maintenance-command behavior explicit and consistent in code, docs, and
  tests.

Decision to make before editing:

- Choose one contract:
  - option A: `validate` and `render` are maintenance mutations
  - option B: `validate` is read-only and `render` is the only explicit
    generated-output rewrite path

Recommended default:

- Option B

Why:

- It preserves a cleaner meaning for `mutated`
- It keeps `validate` closer to inspection / checking
- It limits file-writing behavior to the command whose name already implies
  regeneration

Implementation outline:

- Update `go_ref.py` so `validate_command()` no longer rewrites rendered output
  or session metadata if the repo chooses the read-only path.
- Keep `render_command()` as the explicit regeneration path.
- If the repo instead chooses maintenance mutations, flip `mutated` semantics
  and document that maintenance commands may rewrite generated output.
- Update CLI reference and coder guidance to describe maintenance commands
  explicitly rather than leaving them implied.

Tests to add or update:

- CLI test that `validate` does not change `game.txt` or session metadata if
  the read-only policy is chosen.
- CLI test that `render` updates generated output intentionally.
- Contract test for the `mutated` field on `validate` and `render`.

### ISSUE-005: session `updated_at` semantics

Goal:

- Give `updated_at` one clear meaning and enforce it consistently.

Decision to make before editing:

- Define `updated_at` as one of:
  - session-state changed
  - session-artifact changed
  - any command touched the session

Recommended default:

- `updated_at` means session-state or session-metadata changed, not mere
  read-only inspection

Why:

- It is easier to reason about
- It avoids timestamp churn from maintenance or inspection commands
- It keeps metadata closer to meaningful user-visible changes

Implementation outline:

- Audit all `touch_session_meta()` call sites in `go_ref.py`.
- Remove calls from commands that should be contractually read-only.
- If needed, split helpers into separate meanings such as:
  - state/meta update timestamp helper
  - artifact refresh timestamp helper
- Update docs only if this semantic becomes part of the public session
  lifecycle contract.

Tests to add or update:

- Session metadata test that gameplay mutations advance `updated_at`.
- Test that read-only commands do not advance `updated_at`.
- If `render` is treated specially, test its timestamp behavior explicitly.

### ISSUE-004: `restore_snapshot()` hardcoded config

Goal:

- Remove hidden config literals from shared snapshot restoration.

Implementation outline:

- Inspect the snapshot / restore path in `referee.py`.
- Decide whether the needed config should come from:
  - fields stored in `HistoryEntry`
  - parameters passed into `restore_snapshot()`
  - the source `GameState` when reconstructing
- Prefer preserving config explicitly rather than relying on module constants
  or literals.

Recommended default:

- Extend snapshot/restore flow to preserve `komi`, `handicap`, and any other
  non-board state needed for faithful reconstruction.

Tests to add or update:

- Unit test that undo / restore preserves non-default `komi` and `handicap`.
- Unit test that last-event summary helpers still work correctly after the
  change.

### ISSUE-003: duplicated query parser and dispatch logic

Goal:

- Reduce duplicated `game` / `session` query plumbing without changing CLI
  behavior.

Implementation outline:

- Extract shared parser registration for:
  - `query point`
  - `query chain`
  - `query board`
- Extract shared query execution helper that:
  - reads common query flags
  - routes to `query_point_command()`, `query_chain_command()`, or
    `query_board_command()`
- Keep top-level `game` and `session` command structure intact unless further
  cleanup is clearly low-risk.
- Only consider a command table after the shared helper step if duplication is
  still substantial.

Safety constraints:

- Do not change CLI argument names or ordering semantics.
- Do not change JSON output shape.
- Do not weaken same-target locking behavior.

Tests to keep green:

- all existing query CLI tests
- all non-mutation tests for query commands
- all parallel play/query ordering tests

### ISSUE-002: governance doc boundary cleanup

Goal:

- Move concrete tool-surface details back under the canonical CLI reference and
  keep governance focused on judgment and boundaries.

Implementation outline:

- Trim the tooling appendix in
  `docs/agents/player/gameplay-governance.md` so it references
  `docs/reference/cli.md` for concrete flags and payload shapes.
- Keep the governance-side language that reinforces:
  - informative-only tooling
  - no move recommendation or ranking
  - factual inspection as support for reasoning
- Ensure the player docs still point clearly to the CLI reference for command
  details.

Tests and validation:

- no brittle prose tests
- run Markdown lint
- rely on executable contract tests rather than wording assertions

## Cross-Cutting Validation Plan

Run after each meaningful code change set:

- `python3 -m unittest discover -s tests -v`
- `basedpyright`

Run when rendering or state-transition behavior changes:

- `python3 go_ref.py game validate`

Run when Markdown changes:

- `npm run lint:md`

## Progress Notes

Working assumptions at the start of implementation:

- prefer a read-only `validate` contract
- prefer narrow `updated_at` semantics tied to meaningful session changes
- prefer additive refactors over CLI redesign
- keep governance docs principle-oriented and CLI docs canonical for tool shape
