# Contributing

This repo is a small Python referee and analysis workspace for 9x9 Go.

## Orientation

Read these first:

- [README.md](./README.md)
- [docs/reference/cli.md](./docs/reference/cli.md)
- [go_ref.py](./go_ref.py)
- [referee.py](./referee.py)
- [render.py](./render.py)
- [models.py](./models.py)
- [tests/test_go_ref.py](./tests/test_go_ref.py)

## Working Rules

- Treat `state.json` as authoritative and `game.txt` as generated output.
- Do not hand-edit `state.json` or `game.txt` during normal work.
- Preserve the tool boundary:
  - allowed: legality, captures, ko, chains, liberties, history, rendering,
    canonical state, analysis sessions, undo, validation
  - not allowed: move recommendation, ranking, or score judgment inside the
    referee
- Keep stdout machine-readable JSON for CLI commands.
- Keep human diagnostics on stderr.
- Preserve the CLI contract:
  - mutating `game` and `session` commands update stored state and refresh the
    matching rendered board
  - `show`, `legal`, `chain`, and `query` stay non-mutating
  - `validate` stays read-only; `render` may refresh generated board output
    without changing authoritative state
  - same-target CLI commands remain serialized

## Common Workflow

1. Update code and tests together.
2. Update docs if the command surface or contract changes.
3. Run:

```bash
python3 -m unittest discover -s tests -v
```

4. Run:

```bash
basedpyright
```

5. If rendering or state transitions changed, also run:

```bash
python3 go_ref.py game validate
```

6. If Markdown changed, also run:

```bash
npm run lint:md
```
