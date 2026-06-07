# Codex Coder Guidance

This document is for Codex acting as a coding assistant inside this repo.

## Core Invariants

- `state.json` is authoritative for the canonical game.
- `game.txt` is generated output for the canonical game.
- analysis sessions are authoritative in their own `state.json` files
  under `analysis/sessions/`
- session `game.txt` files are generated output
- mutating `game` and `session` commands must update stored state and refresh
  the matching rendered board
- `show`, `legal`, `chain`, and `query` must not mutate stored state or
  rendered output
- same-target CLI commands must remain serialized
- renderer output is contract-sensitive and should stay deterministic

## Safe Working Rules

- Do not hand-edit `state.json` or `game.txt` during normal work.
- Keep strategy out of the referee.
- Keep stdout JSON stable and machine-readable.
- Keep human diagnostics on stderr.
- Prefer explicit state and target models over clever inference-heavy behavior.

## Code Areas

- [go_ref.py](../../../go_ref.py)
  - CLI surface, target resolution, session lifecycle, locking, JSON contract
- [referee.py](../../../referee.py)
  - legality, captures, ko, undo, tactical queries
- [render.py](../../../render.py)
  - deterministic text rendering
- [models.py](../../../models.py)
  - shared dataclasses and type aliases
- [tests/test_go_ref.py](../../../tests/test_go_ref.py)
  - behavior and contract regression coverage

## Validation

Run:

```bash
python3 -m unittest discover -s tests -v
basedpyright
```

If rendering or state transitions changed, also run:

```bash
python3 go_ref.py game validate
```

If Markdown changed, also run:

```bash
npm run lint:md
```
