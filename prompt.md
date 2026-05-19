# Init prompt

Let's play a game of Go! I'll play White and you play Black. We're playing a 9x9
game. We'll keep track of the game in the `game.txt` file. At the beginning of a
game, initialize `game.txt` from the template at `game-init.txt`.

Ruleset:

We are playing under Japanese rules with 6.5 komi.

You are responsible for knowing and applying the rules of Go, including legal
move validation, captures, ko, pass, end-of-game handling, and scoring.

If I enter an illegal White move, do not update `game.txt` and do not play a
Black response. Instead, briefly tell me the move is illegal and why.

We'll follow GNU-Go's ASCII format to represent the on-going game state.

- Empty intersections: '.'
- Black stones: 'X'
- White stones: 'O'
- Last move is surrounded by parentheses, e.g. '(X)' or '(O)'
- Star/hoshi points: '+'

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
```

Stones wrapped in parenthesis represent the last move. So, after the second move
the board might look like this:

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
```

When asked to start a new game, reinitialize the board from `game-init.txt` and
play your first move as Black.

It is your responsibility to keep the `game.txt` board state up to date after
each move.

After you play a move as Black, wait for me to make a move as White. I will
describe my moves in the letter-number format, such as "c3".

Once I tell you my move:

- update the `game.txt` state
- then decide on your move
- then update the `game.txt` state with your move and report it in chat

You do not need to print `game.txt` in chat, I will have it open in an editor.

Ko will be tracked in the 'Ko:' line as the position where a move is forbidden
by Japanese ko rules. If there is no ko position, put "none" instead.
