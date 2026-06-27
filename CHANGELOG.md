# Changelog

All notable changes to this project will be documented in this file.

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
