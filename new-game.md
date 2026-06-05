# NEW GAME

Let's play a 9x9 game of Go. You are Black and I am White.

Before doing anything else:

1. Read `README.md` and follow it as the operating manual for this repo.
2. Use the referee CLI as the source of truth for legality, captures, ko,
   chains, liberties, move history, and board state.
3. Do not manage the board by hand.
4. Do not edit `game.txt` directly.
5. Try to win the game.

Your workflow for this session:

- Initialize a new canonical game with the referee.
- Use canonical referee commands to understand the position.
- Before each Black move, investigate serious candidates with `query`, `try`,
  and branches when needed.
- If a line is too deep for one short tactical read, create a branch and read
  there.
- Play Black's move by recording it through the CLI.
- After making your move, stop and prompt me for White's move.
- When I reply with a White move, record it through the referee before choosing
  any Black response.
- If my move is illegal, tell me briefly why and ask for another White move.

Move-selection discipline:

- Do not play the first legal move that comes to mind.
- Use `query board` or `show` to identify Black's most urgent problem.
- When the position is nontrivial, investigate more than one serious move.
- Use `query point`, `query chain`, `try play`, and `try sequence` to test
  uncertain candidates.
- Use branches when one short tactical read is not enough or when you want to
  preserve a hypothetical line for further reading.
- Do not resign casually. Read deeper first when a major group seems dead.

Communication style for this game:

- Be brief.
- After your Black move, report the move clearly.
- Then ask for my White move in coordinate form such as `C3`.
- Do not print large dumps of file contents unless needed.
