from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from models import (
    BOARD_SIZE,
    COLUMNS,
    SCHEMA_VERSION,
    CaptureCounts,
    ChainInfo,
    Color,
    Coord,
    GameState,
    HistoryEntry,
    LastMove,
    MoveRecord,
    Point,
    Stone,
)


class RefereeError(Exception):
    code: str
    message: str
    details: dict[str, Any]

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass(slots=True)
class PlayResult:
    applied_move: MoveRecord
    captures: list[Coord]
    capture_count_delta: int
    ko_point: Coord | None
    status: str
    state: dict[str, Any]


def other_color(color: Color) -> Color:
    return "white" if color == "black" else "black"


def color_to_stone(color: Color) -> Stone:
    return color


def stone_to_display(stone: Stone) -> str:
    return {"empty": ".", "black": "X", "white": "O"}[stone]


def parse_coord(coord: str) -> Point:
    if len(coord) < 2:
        raise RefereeError("invalid_coordinate", f"Invalid coordinate: {coord}", {"move": coord})
    text = coord.strip().upper()
    column = text[0]
    row_text = text[1:]
    if column not in COLUMNS:
        raise RefereeError("invalid_coordinate", f"Invalid coordinate: {coord}", {"move": coord})
    if not row_text.isdigit():
        raise RefereeError("invalid_coordinate", f"Invalid coordinate: {coord}", {"move": coord})
    row = int(row_text)
    if row < 1 or row > BOARD_SIZE:
        raise RefereeError("off_board", f"Off-board move: {coord}", {"move": coord})
    x = COLUMNS.index(column)
    y = BOARD_SIZE - row
    return (x, y)


def format_coord(point: Point) -> Coord:
    x, y = point
    return f"{COLUMNS[x]}{BOARD_SIZE - y}"


def on_board(point: Point) -> bool:
    x, y = point
    return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE


def neighbors(point: Point) -> list[Point]:
    x, y = point
    result = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
    return [candidate for candidate in result if on_board(candidate)]


def board_copy(board: list[list[Stone]]) -> list[list[Stone]]:
    return [row[:] for row in board]


def get_stone(board: list[list[Stone]], point: Point) -> Stone:
    x, y = point
    return board[y][x]


def set_stone(board: list[list[Stone]], point: Point, stone: Stone) -> None:
    x, y = point
    board[y][x] = stone


def chain_info(board: list[list[Stone]], point: Point) -> ChainInfo:
    stone = get_stone(board, point)
    if stone == "empty":
        raise RefereeError("empty_point", "Point is empty", {"point": format_coord(point)})
    stones: set[Point] = set()
    liberties: set[Point] = set()
    stack = [point]
    while stack:
        current = stack.pop()
        if current in stones:
            continue
        stones.add(current)
        for neighbor in neighbors(current):
            neighbor_stone = get_stone(board, neighbor)
            if neighbor_stone == stone:
                stack.append(neighbor)
            elif neighbor_stone == "empty":
                liberties.add(neighbor)
    return ChainInfo(stones=stones, liberties=liberties)


def position_hash(state: GameState) -> str:
    payload = {
        "board": state.board,
        "ko_point": state.ko_point,
        "side_to_move": state.side_to_move,
        "status": state.status,
        "capture_counts": state.capture_counts.to_dict(),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def snapshot_state(state: GameState) -> HistoryEntry:
    return HistoryEntry(
        move_number=state.move_number,
        position_hash=position_hash(state),
        board=board_copy(state.board),
        ko_point=state.ko_point,
        capture_counts=CaptureCounts(
            black=state.capture_counts.black,
            white=state.capture_counts.white,
        ),
        side_to_move=state.side_to_move,
        status=state.status,
        last_move=deepcopy(state.last_move),
        move_log=[deepcopy(move) for move in state.move_log],
    )


def restore_snapshot(entry: HistoryEntry, history: list[HistoryEntry]) -> GameState:
    return GameState(
        schema_version=SCHEMA_VERSION,
        board_size=BOARD_SIZE,
        komi=6.5,
        handicap=0,
        status=entry.status,
        move_number=entry.move_number,
        side_to_move=entry.side_to_move,
        ko_point=entry.ko_point,
        capture_counts=CaptureCounts(
            black=entry.capture_counts.black,
            white=entry.capture_counts.white,
        ),
        last_move=deepcopy(entry.last_move),
        board=board_copy(entry.board),
        move_log=[deepcopy(move) for move in entry.move_log],
        history=history,
    )


def state_summary(state: GameState) -> dict[str, Any]:
    return {
        "board_size": state.board_size,
        "komi": state.komi,
        "handicap": state.handicap,
        "status": state.status,
        "move_number": state.move_number,
        "side_to_move": state.side_to_move,
        "ko_point": state.ko_point,
        "capture_counts": state.capture_counts.to_dict(),
        "last_move": state.last_move.to_dict() if state.last_move else None,
    }


def load_state(path: Path) -> GameState:
    if not path.exists():
        raise RefereeError("state_not_found", f"State file not found: {path}", {"state_path": str(path)})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RefereeError("invalid_json", f"Invalid JSON in {path}: {exc.msg}") from exc
    state = GameState.from_dict(data)
    validate_state(state)
    return state


def save_state(path: Path, state: GameState) -> None:
    path.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_state(state: GameState) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    if state.schema_version != SCHEMA_VERSION:
        raise RefereeError("schema_version", "Unsupported schema version", {"schema_version": state.schema_version})
    checks["schema_version"] = True
    if state.board_size != BOARD_SIZE:
        raise RefereeError("board_shape", "Board size must be 9", {"board_size": state.board_size})
    if len(state.board) != BOARD_SIZE or any(len(row) != BOARD_SIZE for row in state.board):
        raise RefereeError("board_shape", "Board must be 9x9")
    valid_stones = {"empty", "black", "white"}
    if any(cell not in valid_stones for row in state.board for cell in row):
        raise RefereeError("board_contents", "Board contains invalid stone values")
    checks["board_shape"] = True
    checks["board_contents"] = True
    if state.move_number != len(state.move_log):
        raise RefereeError("move_log", "Move number does not match move log length")
    checks["move_log"] = True
    if state.move_number == 0:
        if state.last_move is not None:
            raise RefereeError("last_move", "Last move must be null at move 0")
    else:
        if state.last_move is None:
            raise RefereeError("last_move", "Last move is missing")
        last_record = state.move_log[-1]
        if (
            state.last_move.color != last_record.color
            or state.last_move.kind != last_record.kind
            or state.last_move.point != last_record.point
        ):
            raise RefereeError("last_move", "Last move does not match move log")
    checks["last_move"] = True
    if state.capture_counts.black < 0 or state.capture_counts.white < 0:
        raise RefereeError("capture_counts", "Capture counts must be non-negative")
    checks["capture_counts"] = True
    if state.ko_point is not None:
        point = parse_coord(state.ko_point)
        if get_stone(state.board, point) != "empty":
            raise RefereeError("ko_point", "Ko point must be empty", {"ko_point": state.ko_point})
    checks["ko_point"] = True
    valid_status = {"active", "passed", "resigned", "game_over"}
    if state.status not in valid_status:
        raise RefereeError("status", "Invalid game status", {"status": state.status})
    if state.status == "game_over":
        if len(state.move_log) < 2 or state.move_log[-1].kind != "pass" or state.move_log[-2].kind != "pass":
            raise RefereeError("status", "Game over requires consecutive passes")
    if state.status == "resigned":
        if not state.move_log or state.move_log[-1].kind != "resign":
            raise RefereeError("status", "Resigned game must end with resignation")
    checks["status"] = True
    replayed = replay_move_log(state.move_log, state.komi, state.handicap)
    compare_replayed_state(state, replayed)
    checks["turn_order"] = True
    checks["replay"] = True
    return checks


def compare_replayed_state(expected: GameState, replayed: GameState) -> None:
    mismatch = (
        expected.board != replayed.board
        or expected.ko_point != replayed.ko_point
        or expected.side_to_move != replayed.side_to_move
        or expected.status != replayed.status
        or expected.move_number != replayed.move_number
        or expected.capture_counts.to_dict() != replayed.capture_counts.to_dict()
        or (expected.last_move.to_dict() if expected.last_move else None)
        != (replayed.last_move.to_dict() if replayed.last_move else None)
    )
    if mismatch:
        raise RefereeError("replay_mismatch", "Stored state does not match replayed move log")


def ensure_active_turn(state: GameState, color: Color) -> None:
    if state.status in {"resigned", "game_over"}:
        raise RefereeError("game_over", "Game is already over", {"status": state.status})
    if color != state.side_to_move:
        raise RefereeError(
            "wrong_side",
            f"It is {state.side_to_move}'s turn",
            {"expected": state.side_to_move, "actual": color},
        )


def find_captures_after_play(board: list[list[Stone]], played_point: Point, color: Color) -> set[Point]:
    captured: set[Point] = set()
    for neighbor in neighbors(played_point):
        if get_stone(board, neighbor) != other_color(color):
            continue
        info = chain_info(board, neighbor)
        if not info.liberties:
            captured.update(info.stones)
    return captured


def ko_point_for_position(board: list[list[Stone]], played_point: Point, captured: set[Point]) -> Coord | None:
    if len(captured) != 1:
        return None
    played_chain = chain_info(board, played_point)
    if len(played_chain.stones) != 1 or len(played_chain.liberties) != 1:
        return None
    liberty = next(iter(played_chain.liberties))
    return format_coord(liberty)


def is_move_legal(state: GameState, color: Color, move: Coord) -> tuple[bool, str | None]:
    try:
        ensure_active_turn(state, color)
        point = parse_coord(move)
        if state.ko_point == format_coord(point):
            return (False, "ko")
        if get_stone(state.board, point) != "empty":
            return (False, "occupied")
        board = board_copy(state.board)
        set_stone(board, point, color_to_stone(color))
        captured = find_captures_after_play(board, point, color)
        for captured_point in captured:
            set_stone(board, captured_point, "empty")
        info = chain_info(board, point)
        if not info.liberties:
            return (False, "suicide")
        return (True, None)
    except RefereeError as exc:
        return (False, exc.code)


def list_legal_moves(state: GameState, color: Color) -> list[Coord]:
    ensure_active_turn(state, color)
    legal_moves: list[Coord] = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            point = (x, y)
            coord = format_coord(point)
            legal, _ = is_move_legal(state, color, coord)
            if legal:
                legal_moves.append(coord)
    return legal_moves


def apply_play(state: GameState, color: Color, move: Coord) -> PlayResult:
    ensure_active_turn(state, color)
    point = parse_coord(move)
    if state.ko_point == format_coord(point):
        raise RefereeError("illegal_move", "Move is forbidden by ko", {"color": color, "move": move, "reason": "ko"})
    if get_stone(state.board, point) != "empty":
        raise RefereeError(
            "illegal_move",
            "Point is occupied",
            {"color": color, "move": move, "reason": "occupied"},
        )
    previous = snapshot_state(state)
    board = board_copy(state.board)
    set_stone(board, point, color_to_stone(color))
    captured_points = find_captures_after_play(board, point, color)
    for captured_point in captured_points:
        set_stone(board, captured_point, "empty")
    played_chain = chain_info(board, point)
    if not played_chain.liberties:
        raise RefereeError(
            "illegal_move",
            "Suicide is illegal unless it captures",
            {"color": color, "move": move, "reason": "suicide"},
        )
    state.history.append(previous)
    state.board = board
    delta = len(captured_points)
    if color == "black":
        state.capture_counts.black += delta
    else:
        state.capture_counts.white += delta
    state.ko_point = ko_point_for_position(board, point, captured_points)
    state.move_number += 1
    captures = sorted(format_coord(item) for item in captured_points)
    record = MoveRecord(
        number=state.move_number,
        color=color,
        kind="play",
        point=move.upper(),
        captures=captures,
        ko_point_after=state.ko_point,
    )
    state.move_log.append(record)
    state.last_move = LastMove.from_record(record)
    state.side_to_move = other_color(color)
    state.status = "active"
    return PlayResult(
        applied_move=record,
        captures=captures,
        capture_count_delta=delta,
        ko_point=state.ko_point,
        status=state.status,
        state=state_summary(state),
    )


def apply_pass(state: GameState, color: Color) -> dict[str, Any]:
    ensure_active_turn(state, color)
    previous = snapshot_state(state)
    prior_was_pass = bool(state.move_log) and state.move_log[-1].kind == "pass"
    state.history.append(previous)
    state.move_number += 1
    state.ko_point = None
    record = MoveRecord(
        number=state.move_number,
        color=color,
        kind="pass",
        point=None,
        captures=[],
        ko_point_after=None,
    )
    state.move_log.append(record)
    state.last_move = LastMove.from_record(record)
    state.side_to_move = other_color(color)
    state.status = "game_over" if prior_was_pass else "passed"
    return {"applied_move": record.to_dict(), "status": state.status, "state": state_summary(state)}


def apply_resign(state: GameState, color: Color) -> dict[str, Any]:
    ensure_active_turn(state, color)
    previous = snapshot_state(state)
    state.history.append(previous)
    state.move_number += 1
    state.ko_point = None
    record = MoveRecord(
        number=state.move_number,
        color=color,
        kind="resign",
        point=None,
        captures=[],
        ko_point_after=None,
    )
    state.move_log.append(record)
    state.last_move = LastMove.from_record(record)
    state.status = "resigned"
    winner = other_color(color)
    return {
        "applied_move": record.to_dict(),
        "status": state.status,
        "winner": winner,
        "state": state_summary(state),
    }


def chain_at(state: GameState, coord: Coord) -> dict[str, Any]:
    point = parse_coord(coord)
    occupant = get_stone(state.board, point)
    if occupant == "empty":
        return {
            "point": coord.upper(),
            "occupant": "empty",
            "chain": [],
            "liberties": sorted(format_coord(item) for item in neighbors(point) if get_stone(state.board, item) == "empty"),
            "liberty_count": sum(1 for item in neighbors(point) if get_stone(state.board, item) == "empty"),
        }
    info = chain_info(state.board, point)
    return {
        "point": coord.upper(),
        "occupant": occupant,
        "chain": sorted(format_coord(item) for item in info.stones),
        "liberties": sorted(format_coord(item) for item in info.liberties),
        "liberty_count": len(info.liberties),
    }


def undo(state: GameState, count: int) -> dict[str, Any]:
    if count < 1:
        raise RefereeError("invalid_undo", "Undo count must be at least 1", {"count": count})
    if len(state.history) < count:
        raise RefereeError("invalid_undo", "Not enough history to undo", {"count": count})
    history = state.history[:]
    restored: GameState | None = None
    for _ in range(count):
        snapshot = history.pop()
        restored = restore_snapshot(snapshot, history[:])
        history = restored.history[:]
    if restored is None:
        raise RefereeError("invalid_undo", "Nothing to undo")
    state.schema_version = restored.schema_version
    state.board_size = restored.board_size
    state.komi = restored.komi
    state.handicap = restored.handicap
    state.status = restored.status
    state.move_number = restored.move_number
    state.side_to_move = restored.side_to_move
    state.ko_point = restored.ko_point
    state.capture_counts = restored.capture_counts
    state.last_move = restored.last_move
    state.board = restored.board
    state.move_log = restored.move_log
    state.history = restored.history
    return {"undone": count, "state": state_summary(state)}


def replay_move_log(move_log: list[MoveRecord], komi: float, handicap: int) -> GameState:
    state = GameState.new_game()
    state.komi = komi
    state.handicap = handicap
    for record in move_log:
        if record.number != state.move_number + 1:
            raise RefereeError("move_log", "Move numbers must be sequential")
        if record.kind == "play":
            apply_play(state, record.color, record.point or "")
        elif record.kind == "pass":
            apply_pass(state, record.color)
        elif record.kind == "resign":
            apply_resign(state, record.color)
        else:
            raise RefereeError("move_log", "Unknown move kind", {"kind": record.kind})
    return state
