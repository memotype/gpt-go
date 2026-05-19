# Init prompt

Let's play a game of Go! I'll play White and you play Black. We're playing a 9x9
game. We'll keep track of the game in the `game.txt` file. At the beginning of a
game, initialize `game.txt` from the template at `game-init.txt`.

## Ruleset

We are playing under Japanese rules with 6.5 komi.

You are responsible for knowing and applying the rules of Go, including legal
move validation, captures, ko, pass, end-of-game handling, and scoring. This
is not meant to be an explanation of Go, you are expected to understand Go on
at least a basic level.

## Interaction model

This prompt is meant primarily to describe how you and I will communicate a
game of Go through `game.txt` and short chat messages.

If I accidentally enter an illegal White move, do not update `game.txt` and do
not play a Black response. Instead, briefly tell me the move is illegal and why.

We'll follow something resembling GNU-Go's ASCII format to represent the
on-going game state.

- A structured summary of the game state is at the top
- An ASCII representation of the board
  - Numbers and letters surround the ASCII board to represent rows and columns
  - Empty intersections: '.'
  - Black stones: 'X'
  - White stones: 'O'
  - Ko-forbidden position: '~'
  - Each column is separated by either a space, or a parenthesis character
  - Last move is surrounded by parentheses, e.g. '(X)' or '(O)'
    - Parentheses replace spaces
    - Do not put spaces before or after parentheses
    - Keep columns vertically aligned
    - Important:
      - Parentheses replace the spaces around a stone; they do not add extra
        characters.
      - Never write ` (X)` or `(X) ` or ` .(X)` or `(X).`
      - Every row should remain vertically aligned with all other rows.
  - Star/hoshi points: '+'
- Moves are logged in a lower section titled "MOVE LOG"
  - This is not an SGF file, just a list of moves
  - It does not record captures or ko state

We are starting a new game, so reinitialize the board by copying `game-init.txt`
over any existing `game.txt`. Use `game-init.txt` only as a template; maintain
the live game in `game.txt`.

For example, before the first move, the board looks like this:

```txt
Board Size:   9
Handicap      0
Komi:         6.5
Move Number:  0
To Move:      Black
Ko:           none

    White (O) has captured 0 pieces
    Black (X) has captured 0 pieces

    A B C D E F G H J
  9 . . . . . . . . . 9
  8 . . . . . . . . . 8
  7 . . + . . . + . . 7
  6 . . . . . . . . . 6
  5 . . . . + . . . . 5
  4 . . . . . . . . . 4
  3 . . + . . . + . . 3
  2 . . . . . . . . . 2
  1 . . . . . . . . . 1
    A B C D E F G H J

MOVE LOG
========

1.
```

After the first move it might look something like this:

```txt
Board Size:   9
Handicap      0
Komi:         6.5
Move Number:  1
To Move:      White
Ko:           none

    White (O) has captured 0 pieces
    Black (X) has captured 0 pieces

    A B C D E F G H J        Last move: Black G7
  9 . . . . . . . . . 9
  8 . . . . . . . . . 8
  7 . . + . . .(X). . 7
  6 . . . . . . . . . 6
  5 . . . . + . . . . 5
  4 . . . . . . . . . 4
  3 . . + . . . + . . 3
  2 . . . . . . . . . 2
  1 . . . . . . . . . 1
    A B C D E F G H J

MOVE LOG
========

1. G7
```

Stones wrapped in parenthesis represent the last move. *Replace* spaces with the
parentheses, don't insert them before or after parentheses. This keeps the
visual representation visually neat.

Correct:   ` 2 . O(X)O . . . . . 2`
Incorrect: ` 2 . O (X) O . . . . . 2`
Correct:   ` 2(X). . . . . . . . 2`
Incorrect: ` 2 (X). . . . . . . . 2`

Before saving `game.txt`, verify that each board row has exactly 9 intersections.
If the last move was a board move, exactly one intersection should be
parenthesized: the last move. If the last move was pass or resignation, no
intersection should be parenthesized.

So, after the second move the board might look like this:

```txt
Board Size:   9
Handicap      0
Komi:         6.5
Move Number:  2
To Move:      Black
Ko:           none

    White (O) has captured 0 pieces
    Black (X) has captured 0 pieces

    A B C D E F G H J        Last move: White C3
  9 . . . . . . . . . 9
  8 . . . . . . . . . 8
  7 . . + . . . X . . 7
  6 . . . . . . . . . 6
  5 . . . . + . . . . 5
  4 . . . . . . . . . 4
  3 . .(O). . . + . . 3
  2 . . . . . . . . . 2
  1 . . . . . . . . . 1
    A B C D E F G H J

MOVE LOG
========

1. G7
2. C3
```

And move 3 might look like:

```txt
Board Size:   9
Handicap      0
Komi:         6.5
Move Number:  3
To Move:      White
Ko:           none

    White (O) has captured 0 pieces
    Black (X) has captured 0 pieces

    A B C D E F G H J        Last move: Black A3
  9 . . . . . . . . . 9
  8 . . . . . . . . . 8
  7 . . + . . . X . . 7
  6 . . . . . . . . . 6
  5 . . . . . . . . . 5
  4 . . . . . . . . . 4
  3(X). O . . . + . . 3
  2 . . . . . . . . . 2
  1 . . . . . . . . . 1
    A B C D E F G H J

MOVE LOG
========

1. G7
2. C3
3. A3
```

Ko will be tracked in the 'Ko:' line as the position where a move is forbidden
by Japanese ko rules and the forbidden position will be marked with '~' on the
ASCII board. If there is no ko position, put "none" instead.

Treat ~ as empty for liberty/capture purposes, but illegal for the opponent's
immediate move.

"Pass" is also a valid move.

## Interaction rules

It is your responsibility to keep the `game.txt` board state up to date and
valid after each move.

File tools are allowed for reading and editing text. Computational tools,
including scripting tools such as Python, are not allowed for Go analysis.

After you play a move as Black, wait for me to make a move as White. I will
describe my moves in the letter-number format, such as "c3".

Once I tell you my move:

- validate that the move is legal
- update the `game.txt` state and write it out to file
- *then* carefully decide on your move based on the updated game state
  - See "Move selection discipline" section below
- *then* update the `game.txt` state with your move and report it in chat

You do not need to print `game.txt` in chat, I will have it open in an editor.

Ko is live game state.

After each legal move, remove captures, update capture counts, and update `Ko:`
for the next player. Mark a ko-forbidden point with `~`; otherwise write
`Ko: none`. Remove any previous `~` marker when ko is cleared or moved.

When validating a move, check `Ko:` first. A move at the ko-forbidden coordinate
is illegal, even if it would otherwise capture.

Before responding to a White move, internally validate:

1. It is White's turn.
2. The current `Ko:` line is checked before capture analysis.
3. White's move is on-board, empty, not ko-forbidden, and not suicide unless it
   captures.
4. Captures are removed.
5. Capture counts are updated.
6. Ko is updated or cleared for the next player before continuing.
7. Then choose and validate Black's move the same way.

## Move selection discipline

After applying White's legal move, treat the updated `game.txt` position as the
current board before choosing Black's move.

Before choosing Black's move, internally run this move-selection protocol:

1. Restate the position problem for Black in one sentence.
2. Identify 1-3 urgent White threats or Black weaknesses.
3. Identify 2-3 plausible Black candidate moves unless the position has only
   one clearly legal or forcing move.
4. For each serious candidate, read the most obvious immediate White reply.
5. Choose the move that best addresses Black's urgent problem while preserving
   a plausible continuation.

Do not play the first legal move that comes to mind.

You do not need to print this analysis in chat unless I ask. Report only Black's
move after updating `game.txt`.

## Game end

The game ends when both players pass consecutively.

If either player passes, do not change the board stones. Increment the move
number, switch `To Move:`, clear `Ko:` to `none`, append the move as `pass`,
and write `Last move: White pass` or `Last move: Black pass`.

At game end, propose dead stones and final score; do not remove stones until I
agree.

### Resignation

You may resign instead of playing a move.

As Black, you should keep playing while there is any plausible fight, ko,
escape, capture, or life-making sequence. Black may resign when there is no
realistic way to make a living group or recover the game.

If either player resigns, do not play a board move. Append the next move as
`Black resigns` or `White resigns`, leave the board unchanged, and report the
resignation.

## Let's Go

Now, you are playing black, so it's your turn.

Make the first move.

<!-- markdownlint-disable-file MD038 -->