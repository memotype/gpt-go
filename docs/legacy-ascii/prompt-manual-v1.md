# Deprecated Legacy Prompt

This file is preserved only as an archival pointer for the old ASCII-board
workflow.

Do not use this document for current Codex Go sessions.

It reflects an older model where Codex manually maintained `game.txt`, which is
no longer the intended workflow and now conflicts with the repo's actual tool
surface.

Use these documents instead:

1. `README.md`
   - Canonical operating manual
   - Defines the competitive, tool-first workflow
   - Explains `query`, `try`, and `branch`

2. `prompt.md`
   - Canonical session prompt for live Codex-vs-human play
   - Instructs Codex to use the referee CLI as the source of truth
   - Instructs Codex to try to win and analyze deliberately

Current workflow summary:
- never edit `game.txt` directly
- never manage the board by hand
- use canonical commands for the real game
- use `try` for short tactical reading
- use `branch` for persisted deeper reading
