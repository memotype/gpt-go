# Contributing

This repo is a small Python referee for 9x9 Go. The most important
working assumption is that `state.json` is authoritative and `game.txt`
is generated output. If you change game state logic, renderer behavior,
or CLI contracts, treat `state.json` as the source of truth and make
sure `game.txt` remains a deterministic projection of that state.

## Orientation

When starting a fresh session, read these files first:
- [README.md](./README.md)
- [go_ref.py](./go_ref.py)
- [referee.py](./referee.py)
- [render.py](./render.py)
- [models.py](./models.py)
- [tests/test_go_ref.py](./tests/test_go_ref.py)
- [tests/fixtures/renderer](./tests/fixtures/renderer)

Legacy manual-play artifacts are preserved under
[docs/legacy-ascii](./docs/legacy-ascii). They are historical
references and renderer regression fixtures, not the live workflow.

## Working Rules

- Do not hand-edit `game.txt` or `state.json` to advance play unless
  the task is explicitly about repairing corrupted state.
- Preserve the tool boundary:
  - Allowed: legality, captures, ko, chains, liberties, board state,
    pass/resign handling, undo, rendering, validation.
  - Not allowed: move recommendation, candidate ranking, life/death
    judgment, ladder reading, score estimation, territory estimation,
    strategy.
  - Candidate-audit guidance belongs to Codex's reasoning discipline and repo
    prompts, not to referee behavior or CLI output.
- Keep stdout machine-readable JSON for CLI commands.
- Keep human-oriented diagnostics on stderr.
- Prefer small, explicit data-model changes over clever inference-heavy
  code.
- Treat renderer output as contract-sensitive. Small spacing changes can
  break downstream usage and regression expectations.

## Common Workflow

For most code changes:

1. Read the relevant tests in `tests/test_go_ref.py`.
2. Update code.
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
  - If command behavior changes, keep response shapes boring and stable.

- `referee.py`
  - Rules engine.
  - Move legality, captures, suicide handling, ko, undo, replay
    validation live here.
  - This is where rule changes should go first.

- `render.py`
  - Human-facing `game.txt` renderer.
  - Parenthesized last-move formatting is delicate and intentionally tested.

- `models.py`
  - Shared dataclasses and core type aliases.
  - Prefer tightening types here rather than spreading ad hoc dict
    assumptions.

- `tests/test_go_ref.py`
  - Behavioral safety net.
  - Includes rules tests, renderer regressions, and CLI contract checks.

- `tests/fixtures/renderer`
  - Canonical `game.txt` examples used by the renderer regression harness.
  - Helpful when a change should be verified through the CLI end-to-end
    rather than by inspecting `render_text()` alone.

## Expectations for Changes

- If you add or change a command, update `README.md`.
- If you touch any Markdown file, run `npm run lint:md` before considering the
  work complete.
- If you change rules behavior, add or update tests for the exact edge case.
- If you change rendering, compare against the archived manual examples
  and keep regression coverage.
  - Prefer adding or updating a fixture under `tests/fixtures/renderer`
    when the exact `game.txt` output is part of the contract.
- If you change JSON shape, keep backward compatibility in mind or bump
  schema expectations deliberately.

## Type Checking Notes

`basedpyright` is available and useful, but its current warning set is
stricter than the codebase needs in a few places. Right now:

- Fix real errors first.
- Treat `reportUnusedCallResult` warnings as low priority unless they
  hide a real mistake.
- Treat JSON-boundary `Any` warnings as worthwhile only when they affect
  correctness or make core types ambiguous.

If you choose to tighten typing further, do it by clarifying boundaries
and shared types, not by adding busywork.

## State Repair and Debugging

If something looks wrong during play:

1. Run `python3 go_ref.py validate`.
2. Run `python3 go_ref.py show`.
3. Compare `state.json` with `game.txt`.
4. Prefer fixing the underlying state transition bug over patching
   rendered output.

If a test fails around ko or captures, build the smallest board setup
that demonstrates the issue and encode that directly in a test rather
than relying on a long move sequence unless the sequence itself is the
behavior under test.
