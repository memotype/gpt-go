# Changelog

All notable changes to this project will be documented in this file.

## 0.1.7 - 2026-06-27

### Player Guidance

- Changed the detailed gameplay governance so Codex explicitly abandons failed
  local plans once concrete reading shows White can preserve the same bad
  outcome after the strongest obvious reply.
- Changed post-capture and post-loss guidance to require a fresh factual query
  of the affected area before trusting further local reasoning.
- Changed candidate-discipline guidance to reject self-filling and stale
  maintenance moves that do not produce a named concrete result.
- Changed the thin session prompt to delegate strategic judgment back to the
  gameplay-governance doc while preserving the operational command flow.

### Tests

- Changed player-doc regression coverage so the session prompt is validated as
  a thin operational prompt that delegates judgment rules to governance.

## 0.1.6 - 2026-06-27

### Player Docs

- Changed the player governance and session prompt docs to better distinguish
  forced local replies from merely salient local issues, and to require
  whole-board comparison once a local line stops being forcing.
- Changed player-facing guidance to be more skeptical of repeated local
  investment and interior-fill shape moves that improve local statistics
  without changing the expected outcome.
- Changed the player docs index to point readers toward the updated urgency and
  whole-board comparison guidance.
- Changed renderer output so `Last event` appears on the top board row instead
  of creating a separate spacer line above the board.

### Renderer

- Fixed the rendered `game.txt` layout so adding `Last event` no longer creates
  an awkward gap between the top coordinate header and the first board row.
- Fixed renderer validation and regression coverage to support a trailing
  top-row annotation without weakening board-body checks.

## 0.1.5 - 2026-06-27

### Added

- Added explicit lifecycle phases for canonical games and analysis sessions:
  `active`, `scoring`, and `finished`.
- Added `game resume` and `game finalize` commands.
- Added `session resume --name <name>` and `session finalize --name <name>`
  commands.
- Added explicit lifecycle audit events for `resume` and `finalize`.
- Added rendered status and last-event output so scoring and finished states
  are visible in `game.txt`.
- Added tests covering scoring transitions, resume/finalize behavior, command
  restrictions, session parity, undo behavior, JSON output, and rendering.

### Changed

- Changed two consecutive passes to enter `scoring` instead of ending the game
  irreversibly.
- Changed pass resumption semantics so play continues via `resume` rather than
  undoing real pass moves.
- Changed resignation to use the terminal `finished` lifecycle status.
- Changed persisted event handling to keep turn history and lifecycle events in
  one ordered log.
- Changed state validation and replay to understand lifecycle events and legacy
  saved states more safely.
- Changed `legal` command behavior in non-active states to remain
  non-mutating while reporting status-based restrictions.
- Changed CLI and player docs to describe the new scoring/dispute workflow and
  the correct use of `resume` and `finalize`.

### Fixed

- Fixed the semantic bug where reopening play after two passes required
  deleting those passes with `undo`.
- Fixed the lifecycle model so board state, move history, and resumed turn
  order stay consistent through pass disputes.
