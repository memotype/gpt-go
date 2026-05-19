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
  - Each column is separated by either a space, or a parenthesis character
  - Empty intersections: '.'
  - Black stones: 'X'
  - White stones: 'O'
  - Ko-forbidden position: '~'
  - Last move is surrounded by parentheses, e.g. '(X)' or '(O)'
    - Parentheses replace spaces
    - Do not put spaces before or after parentheses
    - Keep columns vertically aligned
  - Star/hoshi points: '+'
- Moves are logged in a lower section titled "MOVE LOG"
  - This is not an SGF file, just a list of moves
  - It does not record captures or ko state

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
visual representation visually neat. So, after the second move the board might
look like this:

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

    A B C D E F G H J        Last move: Black E5
  9 . . . . . . . . . 9
  8 . . . . . . . . . 8
  7 . . + . . . X . . 7
  6 . . . . . . . . . 6
  5 . . . .(X). . . . 5
  4 . . . . . . . . . 4
  3 . . O . . . + . . 3
  2 . . . . . . . . . 2
  1 . . . . . . . . . 1
    A B C D E F G H J

MOVE LOG
========

1. G7
2. C3
3. E5
```

When asked to start a new game, reinitialize the board from `game-init.txt` and
play your first move as Black. Use `game-init.txt` only as a template; maintain
the live game in `game.txt`.

It is your responsibility to keep the `game.txt` board state up to date after
each move.

After you play a move as Black, wait for me to make a move as White. I will
describe my moves in the letter-number format, such as "c3".

Once I tell you my move:

- validate that the move is legal
- update the `game.txt` state
- then decide on your move
- then update the `game.txt` state with your move and report it in chat

You do not need to print `game.txt` in chat, I will have it open in an editor.

Ko will be tracked in the 'Ko:' line as the position where a move is forbidden
by Japanese ko rules and the forbidden position will be marked with '~' on the
ASCII board. If there is no ko position, put "none" instead.

Treat ~ as empty for liberty/capture purposes, but illegal for the opponent’s
immediate move.

Before editing game.txt, internally validate:

1. It is White's turn.
2. White's move is on-board, empty, not ko-forbidden, and not suicide unless it captures.
3. Captures are removed.
4. Capture counts are updated.
5. Ko is updated or cleared.
6. Then choose and validate Black's move the same way.

At game end, propose dead stones and final score; do not remove stones until I agree.
