# Go Referee CLI

This repo provides a 9x9 Go referee and tactical inspection toolkit built for
Codex-driven play and for contributors improving that tooling. The referee is a
deterministic rules and state-management layer: it owns legality, captures, ko,
chains, liberties, move history, and rendered board output, while the player or
calling agent owns strategy.

## What This Project Is For

- running a canonical 9x9 Go game through a CLI
- inspecting tactical facts without hand-managing board state
- simulating short lines and persisted analysis branches
- generating a human-readable `game.txt` view from authoritative state
- evolving the tooling used by "Player Codex" to play and analyze games

## Quickstart

Start a fresh game:

```bash
python3 go_ref.py init
```

Play moves on the canonical game:

```bash
python3 go_ref.py play --color black --move E5
python3 go_ref.py play --color white --move C3
```

Inspect the current position:

```bash
python3 go_ref.py show
python3 go_ref.py query board
```

Read hypothetical lines without mutating the canonical game:

```bash
python3 go_ref.py try play --color black --move D4
python3 go_ref.py try sequence --moves "B:D4,W:C4,B:E4"
```

## Architecture At A Glance

- `state.json`
  - authoritative machine-readable game state
- `game.txt`
  - generated human-readable board view
- `go_ref.py`
  - CLI surface, command dispatch, JSON/stderr contract
- `referee.py`
  - rules engine and tactical query logic
- `render.py`
  - deterministic renderer for `game.txt`
- `analysis/branches/`
  - persisted hypothetical workspaces with their own state and rendered board

The key invariant is simple: `state.json` is the source of truth and
`game.txt` is a deterministic projection of that state.

## Documentation Map

- [docs/reference/cli.md](./docs/reference/cli.md)
  - canonical CLI and tool contract
- [docs/agents/player/](./docs/agents/player/)
  - Codex-as-player guidance for running a Go session
- [docs/agents/coder/](./docs/agents/coder/)
  - Codex-as-coder guidance for safely modifying this project
- [CONTRIBUTING.md](./CONTRIBUTING.md)
  - contributor workflow, expectations, and validation steps
- [docs/legacy-ascii/](./docs/legacy-ascii/)
  - historical manual-play artifacts and renderer regression references

## License

This repository uses a split license:

- Source code and other software artifacts are licensed under
  [MIT](./LICENSE).
- Documentation, prompts, and governance text are licensed under
  [CC BY 4.0](./LICENSE-docs).

In practice, that means the Python code, tests, and tool outputs are MIT,
while the Markdown documentation in the repo root and under `docs/` is
Creative Commons Attribution 4.0 unless a file says otherwise.

## Notes

- Do not hand-edit `state.json` or `game.txt` during normal play.
- Use the referee CLI as the source of truth for mechanics.
- If you change the CLI, renderer, or state-transition behavior, update the
  CLI reference docs and relevant tests together.
