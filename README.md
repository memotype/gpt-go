# gpt-go: A 9x9 Go Referee for LLM Tool-Use Experiments

This repository is a 9x9 Go referee and analysis workspace built for studying
LLM tool use, working memory, and sequential reasoning. It uses Go as a compact
but tactically demanding environment: small enough to inspect closely, hard
enough that state tracking and disciplined reading still matter.

The project is not trying to prove that an LLM can already play strong Go. It
is an experiment in whether a model reasons more reliably when deterministic
game mechanics and bounded inspection tools are handled outside the model.

## What This Is

- A local 9x9 Go referee with deterministic rule enforcement
- A CLI that stores canonical game state and refreshes rendered board output
- A workspace for isolated hypothetical analysis sessions
- An experiment in tool design for agent reasoning

## What This Is Not

- Not a Go engine
- Not a KataGo wrapper
- Not a move recommender
- Not a live-game assistant
- Not a hidden strategy layer that quietly tells the model what to play

The referee owns facts. The model remains responsible for judgment.

## Why This Experiment Exists

LLMs can sound confident while quietly losing track of board state, move order,
captures, ko, or the consequences of a tactical sequence. Narrative fluency is
not the same thing as reliable state tracking.

This repository explores a narrower question: if the model can ask a
deterministic tool for legal moves, chain structure, board summaries, and
hypothetical branches, does its reasoning improve because the facts are more
stable?

The design goal is to support reasoning without embedding the answer inside the
tools. The referee handles mechanics and persistence. The model still has to
decide what matters strategically.

## Core Design Principles

- `state.json` is the authoritative canonical game state.
- `game.txt` is generated board output for humans.
- `python3 go_ref.py game ...` subcommands operate on the canonical game.
- `python3 go_ref.py session ...` subcommands operate on isolated hypothetical
  branches under `analysis/sessions/<name>/`.
- Mutating `python3 go_ref.py` subcommands update stored state and refresh the
  matching rendered board.
- The `show`, `legal`, `chain`, and `query` subcommands remain non-mutating.
- CLI stdout stays machine-readable JSON.
- Human-readable board rendering is written to files, not mixed into JSON.
- Rule enforcement, captures, ko, undo, validation, and rendering stay inside
  the referee.
- Strategy, prioritization, and move selection stay outside the referee.

The detailed CLI contract lives in `docs/reference/cli.md`.

## Quick Start

Prerequisite: Python 3. The referee currently has no separate Python
package-install step.

```bash
git clone https://github.com/memotype/gpt-go.git
cd gpt-go
python3 go_ref.py game init
python3 go_ref.py game play --color black --move E5
cat game.txt
```

The `go_ref.py` commands emit raw JSON on stdout. That output is designed
primarily for agents, scripts, and automation. The human-readable board view
lives in `game.txt`, which mutating commands refresh for you.

If you are using Codex CLI, a practical workflow is to keep `game.txt` visible
in another terminal pane or editor tab while the agent interacts with the
referee. If you are using Codex through an IDE integration such as VS Code, the
same idea applies there too. None of that is required, though; the repository
also works fine as a normal command-line tool for humans.

For machine-readable inspection, use commands such as:

```bash
python3 go_ref.py game show
python3 go_ref.py game query board
```

## Example Workflow

The canonical game and hypothetical sessions are intentionally separate.

Start a fresh canonical game, play a move, inspect the rendered board, and then
query machine-readable state:

```bash
python3 go_ref.py game init
python3 go_ref.py game play --color black --move E5
cat game.txt
python3 go_ref.py game query board
```

Verified JSON excerpt from `game play`:

```json
{
  "command": "game",
  "ok": true,
  "result": {
    "applied_move": {
      "captures": [],
      "color": "black",
      "kind": "play",
      "ko_point_after": null,
      "number": 1,
      "point": "E5",
      "reason": null
    },
    "capture_count_delta": 0,
    "captures": [],
    "ko_point": null,
    "mutated": true,
    "state": {
      "board_size": 9,
      "capture_counts": {
        "black": 0,
        "white": 0
      },
      "event_number": 1,
      "handicap": 0,
      "ko_point": null,
      "komi": 6.5,
      "last_move": {
        "color": "black",
        "kind": "play",
        "point": "E5"
      },
      "move_number": 1,
      "side_to_move": "white",
      "status": "active"
    },
    "status": "active",
    "target": {
      "game_path": "game.txt",
      "kind": "game",
      "meta_path": null,
      "name": null,
      "state_path": "state.json"
    }
  }
}
```

Verified `game.txt` after that move:

```text
Board Size:   9
Handicap      0
Komi:         6.5
Status:       Active
Event Number: 1
Move Number:  1
To Move:      White
Ko:           none

    White (O) has captured 0 pieces
    Black (X) has captured 0 pieces

    A B C D E F G H J        Last move: Black E5
  9 . . . . . . . . . 9      Last event: Black E5
  8 . . . . . . . . . 8
  7 . . + . . . + . . 7
  6 . . . . . . . . . 6
  5 . . . .(X). . . . 5
  4 . . . . . . . . . 4
  3 . . + . . . + . . 3
  2 . . . . . . . . . 2
  1 . . . . . . . . . 1
    A B C D E F G H J

MOVE LOG
========

1. E5
```

Go coordinates conventionally skip the letter `I`, so the board columns run
`A B C D E F G H J`.

Create a hypothetical session from the current canonical state:

```bash
python3 go_ref.py session create --name center-read
python3 go_ref.py session play --name center-read --color white --move D5
python3 go_ref.py session query --name center-read board
python3 go_ref.py game show
```

Verified JSON excerpt from the session query:

```json
{
  "command": "session",
  "ok": true,
  "result": {
    "capture_counts": {
      "black": 0,
      "white": 0
    },
    "chain_summary": {
      "black_chain_count": 1,
      "white_chain_count": 1
    },
    "ko_point": null,
    "mutated": false,
    "side_to_move": "black",
    "status": "active",
    "target": {
      "game_path": "analysis/sessions/center-read/game.txt",
      "kind": "session",
      "meta_path": "analysis/sessions/center-read/meta.json",
      "name": "center-read",
      "state_path": "analysis/sessions/center-read/state.json"
    }
  }
}
```

The important distinction is that the session now contains both `E5` and `D5`,
while the canonical game still contains only the original `E5` move until you
choose to record something on `game`.

## Repository Guide

- `go_ref.py`: CLI entrypoint, target resolution, locking, session
  lifecycle, and JSON output contract
- `referee.py`: rules, legality, captures, ko, undo, validation,
  and tactical queries
- `render.py`: deterministic text rendering for `game.txt`
- `models.py`: shared dataclasses and persisted state model
- `tests/test_go_ref.py`: rules, renderer, concurrency,
  and CLI contract coverage
- `docs/reference/cli.md`: canonical CLI reference
- `docs/agents/`: guidance for agent-facing workflows in this
  repo
- `CONTRIBUTING.md`: contributor workflow and validation
  expectations
- `pyproject.toml`: Python project metadata, contributor extras, and
  PyMarkdown configuration
- `pyrightconfig.json`: static analysis scope

## Contributor Checks

The repository emphasizes executable contracts over vague behavior claims.

- Unit tests cover rules, rendering, query behavior, session isolation, and the
  CLI's JSON contract.
- Same-target CLI commands are serialized so state and rendered output stay in
  sync under concurrent access.
- `validate` is read-only validation of authoritative state.
- `render` refreshes generated board output without changing authoritative
  state.
- `basedpyright` is used for static analysis.
- `pymarkdown --strict-config scan --recurse .` checks Markdown docs.

Install contributor tools with:

```bash
python3 -m pip install -e '.[dev]'
```

Common contributor checks:

```bash
python3 -m unittest discover -s tests -v
basedpyright
pymarkdown --strict-config scan --recurse .
```

For docs-only changes, `pymarkdown --strict-config scan --recurse .` is the
minimum expected check.

## Current Scope And Limitations

- The referee does not evaluate positions like a strong Go engine.
- It does not recommend moves or rank candidate plays.
- It does not guarantee strong play by an LLM using the tools.
- It is intended for local experimentation, analysis, and development.
- It should not be used in contexts where external assistance violates the
  rules.
- The tool layer is intentionally constrained so strategy is not smuggled into
  the referee implementation.

## Contributing And License

Contributing guidance lives in `CONTRIBUTING.md`.

The code is available under the MIT License in `LICENSE`. Documentation
licensing details are in `LICENSE-docs`.
