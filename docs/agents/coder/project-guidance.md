# Codex Coder Guidance

This document is for Codex acting as a coding assistant inside this repo.

## Purpose

The project exists to support a Go-playing agent with deterministic referee and
analysis tools. When changing code, optimize for making the tool safer,
clearer, and more reliable for "Player Codex."

## Core Invariants

- `state.json` is authoritative.
- `game.txt` is generated output.
- canonical and branch `play`, `pass`, `resign`, and `undo` must update stored
  state and refresh the matching rendered board.
- `query` and `try` must not mutate stored state or rendered output.
- same-target CLI processes must remain serialized so concurrent commands
  cannot race `state.json` and `game.txt`.
- renderer output is contract-sensitive and should remain deterministic.

## Safe Working Rules

- Do not hand-edit `state.json` or `game.txt` during normal work.
- Preserve the tool boundary:
  - rules and mechanics belong in the referee
  - strategy and move recommendation do not
- Keep stdout JSON stable and machine-readable.
- Keep human diagnostics on stderr.
- Prefer explicit state-model changes over clever inference-heavy behavior.

## Code Areas

- `go_ref.py`
  - CLI surface, command dispatch, JSON contract, target locking
- `referee.py`
  - legality, captures, ko, undo, tactical query logic
- `render.py`
  - human-facing board rendering and file projection
- `models.py`
  - shared dataclasses and type aliases
- `tests/test_go_ref.py`
  - behavior and contract regression coverage

## Expectations For Changes

- If command behavior changes, update
  [../../reference/cli.md](../../reference/cli.md).
- If gameplay-facing operating rules change, update
  [../player/gameplay-governance.md](../player/gameplay-governance.md).
- If rendering or state-transition behavior changes, prefer adding exact
  regression coverage rather than relying on manual inspection.
- If JSON shape changes, do so deliberately and document the contract change.

## Validation

For most changes, run:

```bash
python3 -m unittest discover -s tests -v
basedpyright
```

If rendering or state transitions changed, also run:

```bash
python3 go_ref.py validate
```

If Markdown changed, also run:

```bash
npm run lint:md
```
