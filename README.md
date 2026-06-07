# Go Referee CLI

This repo provides a 9x9 Go referee and analysis workspace for Codex-driven
play and development. The referee owns deterministic game mechanics and state
transitions. Strategy stays outside the tool.

## Core Model

- `state.json`
  - authoritative canonical game state
- `game.txt`
  - generated human-readable rendering of canonical state
- `analysis/sessions/<name>/state.json`
  - authoritative state for one analysis session
- `analysis/sessions/<name>/game.txt`
  - generated rendering for one analysis session
- `analysis/sessions/<name>/meta.json`
  - session metadata

Canonical play lives under `game`. Hypothetical reading lives under
`session`.

## Quickstart

Start a fresh canonical game:

```bash
python3 go_ref.py game init
```

Play on the canonical game:

```bash
python3 go_ref.py game play --color black --move E5
python3 go_ref.py game play --color white --move C3
```

Inspect the canonical game:

```bash
python3 go_ref.py game show
python3 go_ref.py game query board
```

Create an analysis session from canonical state:

```bash
python3 go_ref.py session create --name center-read
python3 go_ref.py session play --name center-read --color black --move D4
python3 go_ref.py session query board --name center-read
```

Create an ephemeral session for quick reading:

```bash
python3 go_ref.py session temp --from game
```

## Architecture At A Glance

- [go_ref.py](./go_ref.py)
  - CLI surface, target resolution, locking, JSON contract
- [referee.py](./referee.py)
  - rules engine, legality, captures, ko, tactical queries
- [render.py](./render.py)
  - deterministic text rendering
- [models.py](./models.py)
  - shared dataclasses and type aliases
- [docs/reference/cli.md](./docs/reference/cli.md)
  - canonical CLI reference
- [tests/test_go_ref.py](./tests/test_go_ref.py)
  - rules, rendering, and CLI contract coverage

## Notes

- Do not hand-edit `state.json` or `game.txt` during normal work.
- Mutating `game` and `session` commands update stored state and refresh the
  matching rendered board.
- Query-style commands stay non-mutating.
- Same-target CLI commands remain serialized so concurrent processes do not
  race state and rendered output.
