from __future__ import annotations

import re
from pathlib import Path

from models import BOARD_SIZE, HOSHI_POINTS, GameState
from referee import format_coord, stone_to_display


def format_player(color: str) -> str:
    return color.capitalize()


def format_ko(ko_point: str | None) -> str:
    return ko_point if ko_point is not None else "none"


def format_last_move(state: GameState) -> str | None:
    if state.last_move is None:
        return None
    if state.last_move.kind == "play":
        return f"{format_player(state.last_move.color)} {state.last_move.point}"
    if state.last_move.kind == "pass":
        return f"{format_player(state.last_move.color)} pass"
    return f"{format_player(state.last_move.color)} resign"


def display_symbol(state: GameState, x: int, y: int) -> str:
    coord = format_coord((x, y))
    stone = state.board[y][x]
    if stone == "empty" and state.ko_point == coord:
        return "~"
    if stone == "empty" and coord in HOSHI_POINTS:
        return "+"
    return stone_to_display(stone)


def render_row(state: GameState, row_number: int) -> str:
    y = BOARD_SIZE - row_number
    cells: list[str] = []
    last_index: int | None = None
    for x in range(BOARD_SIZE):
        coord = format_coord((x, y))
        symbol = display_symbol(state, x, y)
        if state.last_move is not None and state.last_move.kind == "play" and state.last_move.point == coord:
            last_index = x
        cells.append(symbol)
    body = list(" ".join(cells))
    if last_index is not None:
        symbol_index = last_index * 2
        if last_index == 0:
            body.insert(0, "(")
            symbol_index += 1
        else:
            body[symbol_index - 1] = "("
        if last_index == BOARD_SIZE - 1:
            body.append(")")
        else:
            body[symbol_index + 1] = ")"
    return f"  {row_number} {''.join(body)} {row_number}"


def render_move_log(state: GameState) -> list[str]:
    lines = ["MOVE LOG", "========", ""]
    for move in state.move_log:
        suffix = move.point if move.kind == "play" else move.kind
        lines.append(f"{move.number}. {suffix}")
    if state.move_number == 0:
        lines.append("1.")
    return lines


def render_text(state: GameState) -> str:
    last_move = format_last_move(state)
    lines = [
        f"Board Size:   {state.board_size}",
        f"Handicap      {state.handicap}",
        f"Komi:         {state.komi}",
        f"Move Number:  {state.move_number}",
        f"To Move:      {format_player(state.side_to_move)}",
        f"Ko:           {format_ko(state.ko_point)}",
        "",
        f"    White (O) has captured {state.capture_counts.white} pieces",
        f"    Black (X) has captured {state.capture_counts.black} pieces",
        "",
    ]
    header = "    A B C D E F G H J"
    if last_move is not None:
        header = f"{header}        Last move: {last_move}"
    lines.append(header)
    for row_number in range(BOARD_SIZE, 0, -1):
        lines.append(render_row(state, row_number))
    lines.append("    A B C D E F G H J")
    lines.append("")
    lines.extend(render_move_log(state))
    return "\n".join(lines)


def validate_rendered_text(state: GameState, text: str) -> None:
    board_rows = [line for line in text.splitlines() if line.startswith("  ") and line[2:3].isdigit()]
    last_move_count = sum(row.count("(X)") + row.count("(O)") for row in board_rows)
    expected = 1 if state.last_move is not None and state.last_move.kind == "play" else 0
    if last_move_count != expected:
        raise ValueError("Rendered board has incorrect parenthesized last-move count")
    for row_number in range(BOARD_SIZE, 0, -1):
        marker = f"  {row_number} "
        row = next(line for line in text.splitlines() if line.startswith(marker))
        body = row[len(marker) : -len(f" {row_number}")]
        cells = re.findall(r"\([XO]\)|[.XO+~]", body)
        if len(cells) != BOARD_SIZE:
            raise ValueError(f"Rendered row {row_number} does not contain 9 intersections")


def render_to_path(state: GameState, path: Path) -> str:
    text = render_text(state)
    validate_rendered_text(state, text)
    path.write_text(text, encoding="utf-8")
    return text
