# Contributing

This repo is a small Python referee and tactical inspection toolkit for 9x9
Go. The core engineering contract is that `state.json` is authoritative and
`game.txt` is generated output. Changes to rules, rendering, or CLI behavior
should preserve that contract.

## Orientation

Read these first when getting started:

- [README.md](./README.md)
- [docs/reference/cli.md](./docs/reference/cli.md)
- [go_ref.py](./go_ref.py)
- [referee.py](./referee.py)
- [render.py](./render.py)
- [models.py](./models.py)
- [tests/test_go_ref.py](./tests/test_go_ref.py)

If you are working as an agent inside this repo, the project-specific agent
guidance lives under:

- [docs/agents/coder/](./docs/agents/coder/)
- [docs/agents/player/](./docs/agents/player/)

Legacy manual-play artifacts are preserved under
[docs/legacy-ascii](./docs/legacy-ascii). They are historical references and
renderer regression fixtures, not the live workflow.

## Licensing

This repository uses a split license:

- Code contributions are accepted under the terms of [MIT](./LICENSE).
- Documentation, prompt, and governance contributions are accepted under the
  terms of [CC BY 4.0](./LICENSE-docs).

If a contribution spans both code and docs, each part follows the license of
the file it is added to or modifies.

## Working Rules

- Do not hand-edit `game.txt` or `state.json` to advance play unless the task
  is explicitly about repairing corrupted state.
- Preserve the tool boundary:
  - Allowed: legality, captures, ko, chains, liberties, board state,
    pass/resign handling, undo, rendering, validation, and tactical
    hypotheticals.
  - Not allowed: move recommendation, candidate ranking, life/death judgment,
    ladder reading, or score estimation inside the referee itself.
- Keep stdout machine-readable JSON for CLI commands.
- Keep human-oriented diagnostics on stderr.
- Prefer small, explicit data-model changes over inference-heavy behavior.
- Treat renderer output as contract-sensitive. Small spacing changes can break
  downstream usage and regression expectations.
- Preserve the CLI state/render contract:
  - canonical and branch `play`, `pass`, `resign`, and `undo` update
    `state.json` and refresh `game.txt` for the same target
  - `query` and `try` commands do not mutate stored state or rendered output
  - same-target CLI processes remain serialized so concurrent commands cannot
    race `state.json` and `game.txt`

## Common Workflow

For most code changes:

1. Read the relevant tests in `tests/test_go_ref.py`.
2. Update code and docs together if the contract changes.
3. Run:

```bash
python3 -m unittest discover -s tests -v
```

4. Run:

```bash
basedpyright
```

5. If the change touches rendering or state transitions, also run:

```bash
python3 go_ref.py validate
```

6. If the change touches any Markdown file, also run:

```bash
npm run lint:md
```

## File Guide

- `go_ref.py`
  - CLI surface and JSON/stderr behavior.
- `referee.py`
  - Rules engine and tactical queries.
- `render.py`
  - Human-facing `game.txt` renderer.
- `models.py`
  - Shared dataclasses and type aliases.
- `tests/test_go_ref.py`
  - Rules, rendering, and CLI contract coverage.
- `tests/fixtures/renderer`
  - Canonical rendered board fixtures used for regression checks.

## Expectations For Changes

- If you add or change a command, update
  [docs/reference/cli.md](./docs/reference/cli.md).
- If you change rules behavior, add or update tests for the exact edge case.
- If you change rendering, keep regression coverage and compare against the
  archived manual examples when useful.
- If you change JSON shape, keep backward compatibility in mind or update the
  schema contract deliberately.

## State Repair And Debugging

If something looks wrong during play:

1. Run `python3 go_ref.py validate`.
2. Run `python3 go_ref.py show`.
3. Compare `state.json` with `game.txt`.
4. Fix the underlying state-transition bug rather than patching rendered
   output.
