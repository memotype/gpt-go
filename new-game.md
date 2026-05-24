Let's play a 9x9 game of Go. You are Black and I am White.

Before doing anything else:

1. Read `README.md` and follow it as the operating manual for this repo.
2. Use the provided referee CLI as the source of truth for legality, captures,
   ko, chains, liberties, move history, and board state.
3. Do not manage the board by hand and do not edit `game.txt` directly.

Your workflow for this session:

- Initialize a new game with the referee.
- Use the referee-managed files and commands to understand the current position.
- Play the first move as Black by recording it through the CLI.
- After making your move, stop and prompt me for White's move.
- When I reply with a White move, record it through the referee before choosing
  any Black response.
- If needed, use the referee for mechanical questions like legality, captures,
  ko, chains, and liberties.
- Do not provide strategic analysis unless I explicitly ask for it.
- Do not use raw manual analysis of script-managed assets when the referee can
  answer the question directly.

Communication style for this game:

- Be brief.
- After your Black move, report the move clearly.
- Then ask for my White move in coordinate form such as `C3`.
- If my move is illegal, tell me briefly why and ask for another White move.
- Do not print large dumps of file contents unless needed.

Start now:
- Read `README.md`
- Initialize the game
- Play Black's first move
- Ask me for White's reply
