# Coding Session Prompt

Use this as the thin session-start prompt for Codex when starting a coding
session in this repo:

```md
We are working in the 9x9 Go referee repo.

Before doing anything else:

1. Read `README.md`.
2. Read `CONTRIBUTING.md`.
3. Read `docs/reference/cli.md`.
4. Read `docs/agents/coder/project-guidance.md`.

When making changes:

- Treat `state.json` as authoritative and `game.txt` as generated output.
- Never hand-edit `state.json` or `game.txt` during normal work.
- Preserve the CLI contract:
  - mutating commands update state and refresh the rendered board
  - `query` and `try` stay non-mutating
  - same-target CLI commands stay serialized
- Keep stdout machine-readable JSON for CLI commands.
- Update docs and tests when behavior or contracts change.

Before considering the work complete:

1. Run `python3 -m unittest discover -s tests -v`.
2. Run `basedpyright`.
3. If rendering or state transitions changed, run `python3 go_ref.py validate`.
4. If Markdown changed, run `npm run lint:md`.
```

This prompt is intentionally thin. The detailed coding guidance lives in:

- [../../reference/cli.md](../../reference/cli.md)
- [./project-guidance.md](./project-guidance.md)
- [../../../CONTRIBUTING.md](../../../CONTRIBUTING.md)
