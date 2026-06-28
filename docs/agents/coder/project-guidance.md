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
- `validate` should remain read-only; `render` may refresh generated output
  without changing authoritative state
- same-target CLI commands must remain serialized
- renderer output is contract-sensitive and should stay deterministic

## Safe Working Rules

- Do not hand-edit `state.json` or `game.txt` during normal work.
- Keep strategy out of the referee.
- Keep stdout JSON stable and machine-readable.
- Keep human diagnostics on stderr.
- Prefer explicit state and target models over clever inference-heavy behavior.

## Guidance For Player-Protocol Changes

When updating player prompts or gameplay-governance docs, optimize for better
judgment, not more ritual.

- Good changes add guardrails against known failure modes such as stopping
  reading too early, confusing legality with quality, or trusting one-ply
  severity without checking the opponent's strongest reply.
- Good changes preserve room for Codex to reason about shape, life, thickness,
  sacrifice, efficiency, and whole-board tradeoffs.
- Avoid turning strategy guidance into a move-selection algorithm or rigid
  checklist.
- Prefer principle-based wording over over-prescriptive procedures.

In general:

- hard rules should protect mechanics, state discipline, and forced-line
  reading hygiene
- strategic guidance should stay flexible and judgment-oriented

If a docs change would make Codex more compliant but less thoughtful, revise it
toward clearer principles instead of adding more steps.

Do not treat prose guidance as a contract that requires brittle wording tests.
If documentation needs regression coverage at all, prefer tests for stable
interfaces, CLI behavior, JSON shape, or other executable contracts rather
than exact phrases inside governance text.

## Experimental Boundary

This repo exists to study GPT/Codex's ability to reason about Go without
quietly turning the referee or tool layer into a Go engine.

Treat the tools as:

- Codex's eyes into the position
- Codex's working memory for canonical and hypothetical state
- Codex's source of deterministic mechanics

Do not turn the tools into:

- a move recommender
- a candidate ranker
- a life-and-death oracle
- a territory or score judge
- a hidden strategic policy encoded in Python

In short, the referee and session workspace may manage state, legality,
captures, ko, rendering, and tactical inspection, but the actual Go judgment
should remain in Codex's reasoning rather than being smuggled into the tools.

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
