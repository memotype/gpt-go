from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from models import (
    BOARD_SIZE,
    COLUMNS,
    SCHEMA_VERSION,
    CaptureCounts,
    ChainInfo,
    Color,
    Coord,
    EventKind,
    GameState,
    GameStatus,
    HistoryEntry,
    LastMove,
    MoveRecord,
    Point,
    Stone,
    TurnKind,
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


SequenceActionKind = TurnKind


@dataclass(slots=True)
class SequenceStep:
    color: Color
    kind: SequenceActionKind
    move: Coord | None


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


def clone_state(state: GameState) -> GameState:
    return GameState.from_dict(state.to_dict())


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


def chain_anchor(stones: set[Point]) -> Coord:
    return min(format_coord(point) for point in stones)


def chain_payload(board: list[list[Stone]], info: ChainInfo) -> dict[str, Any]:
    return {
        "color": get_stone(board, next(iter(info.stones))),
        "stones": sorted(format_coord(item) for item in info.stones),
        "liberties": sorted(format_coord(item) for item in info.liberties),
        "liberty_count": len(info.liberties),
        "in_atari": len(info.liberties) == 1,
        "anchor": chain_anchor(info.stones),
    }


def compact_chain_payload(board: list[list[Stone]], info: ChainInfo) -> dict[str, Any]:
    payload = chain_payload(board, info)
    return {
        "anchor": payload["anchor"],
        "color": payload["color"],
        "stones": payload["stones"],
        "liberties": payload["liberties"],
        "liberty_count": payload["liberty_count"],
        "in_atari": payload["in_atari"],
    }


def enumerate_chains(board: list[list[Stone]]) -> list[dict[str, Any]]:
    seen: set[Point] = set()
    chains: list[dict[str, Any]] = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            point = (x, y)
            stone = get_stone(board, point)
            if stone == "empty" or point in seen:
                continue
            info = chain_info(board, point)
            seen.update(info.stones)
            payload = chain_payload(board, info)
            chains.append(payload)
    return chains


def enumerate_empty_regions(board: list[list[Stone]]) -> list[dict[str, Any]]:
    seen: set[Point] = set()
    regions: list[dict[str, Any]] = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            point = (x, y)
            if point in seen or get_stone(board, point) != "empty":
                continue
            region_points: set[Point] = set()
            bordering_colors: set[Color] = set()
            bordering_chain_anchors: set[Coord] = set()
            stack = [point]
            while stack:
                current = stack.pop()
                if current in region_points:
                    continue
                region_points.add(current)
                seen.add(current)
                for neighbor in neighbors(current):
                    neighbor_stone = get_stone(board, neighbor)
                    if neighbor_stone == "empty":
                        if neighbor not in region_points:
                            stack.append(neighbor)
                        continue
                    bordering_colors.add(neighbor_stone)
                    bordering_chain_anchors.add(chain_anchor(chain_info(board, neighbor).stones))
            regions.append(
                {
                    "points": sorted(format_coord(item) for item in region_points),
                    "bordering_colors": sorted(bordering_colors),
                    "bordering_chain_anchors": sorted(bordering_chain_anchors),
                }
            )
    regions.sort(key=lambda region: region["points"])
    return regions


def validate_local_radius(local_radius: int | None) -> int | None:
    if local_radius is None:
        return None
    if local_radius < 1 or local_radius > 4:
        raise RefereeError(
            "invalid_query_argument",
            "Local radius must be between 1 and 4",
            {"local_radius": local_radius},
        )
    return local_radius


def validate_liberty_threshold(liberty_threshold: int) -> int:
    if liberty_threshold < 1:
        raise RefereeError(
            "invalid_query_argument",
            "Liberty threshold must be at least 1",
            {"liberty_threshold": liberty_threshold},
        )
    return liberty_threshold


def build_local_view(state: GameState, center: Point, radius: int) -> dict[str, Any]:
    min_x = max(0, center[0] - radius)
    max_x = min(BOARD_SIZE - 1, center[0] + radius)
    min_y = max(0, center[1] - radius)
    max_y = min(BOARD_SIZE - 1, center[1] + radius)
    rows: list[dict[str, Any]] = []
    last_move_point = parse_coord(state.last_move.point) if state.last_move and state.last_move.point else None
    for y in range(min_y, max_y + 1):
        row_number = BOARD_SIZE - y
        cells: list[dict[str, Any]] = []
        for x in range(min_x, max_x + 1):
            point = (x, y)
            cells.append(
                {
                    "coord": format_coord(point),
                    "occupant": get_stone(state.board, point),
                    "is_center": point == center,
                    "is_last_move": point == last_move_point,
                }
            )
        rows.append({"row": row_number, "cells": cells})
    return {
        "center": format_coord(center),
        "radius": radius,
        "bounds": {
            "min": format_coord((min_x, max_y)),
            "max": format_coord((max_x, min_y)),
        },
        "rows": rows,
    }


def compact_chain_map(board: list[list[Stone]]) -> dict[Coord, dict[str, Any]]:
    return {payload["anchor"]: payload for payload in enumerate_chains(board)}


def chain_signature(chain_data: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    return (str(chain_data["color"]), tuple(cast(list[str], chain_data["stones"])))


def diff_chain_maps(
    before_map: dict[Coord, dict[str, Any]],
    after_map: dict[Coord, dict[str, Any]],
) -> dict[str, Any]:
    before_by_signature = {chain_signature(item): item for item in before_map.values()}
    after_by_signature = {chain_signature(item): item for item in after_map.values()}
    changed_entries: list[dict[str, Any]] = []
    changed_anchors: set[Coord] = set()
    signatures = sorted(set(before_by_signature) | set(after_by_signature))
    for signature in signatures:
        before = before_by_signature.get(signature)
        after = after_by_signature.get(signature)
        color = before["color"] if before is not None else after["color"] if after is not None else None
        if color is None:
            continue
        if before is None and after is not None:
            status = "added"
        elif before is not None and after is None:
            status = "removed"
        elif before == after:
            continue
        else:
            status = "modified"
        anchor_before = before["anchor"] if before else None
        anchor_after = after["anchor"] if after else None
        if anchor_before is not None:
            changed_anchors.add(anchor_before)
        if anchor_after is not None:
            changed_anchors.add(anchor_after)
        changed_entries.append(
            {
                "anchor_before": anchor_before,
                "anchor_after": anchor_after,
                "color": color,
                "status": status,
                "stones_before": before["stones"] if before else [],
                "stones_after": after["stones"] if after else [],
                "liberty_count_before": before["liberty_count"] if before else None,
                "liberty_count_after": after["liberty_count"] if after else None,
            }
        )
    changed_entries.sort(
        key=lambda item: (
            str(item["color"]),
            str(item["anchor_after"] or item["anchor_before"] or ""),
            str(item["status"]),
        )
    )
    return {
        "changed_chain_anchors": sorted(changed_anchors),
        "changed_chains": changed_entries,
    }


def build_last_event_summary(state: GameState) -> dict[str, Any] | None:
    if not state.history:
        return None
    previous = restore_snapshot(
        state.history[-1],
        state.history[:-1],
        schema_version=state.schema_version,
        board_size=state.board_size,
        komi=state.komi,
        handicap=state.handicap,
    )
    event = last_event(state)
    diff = diff_chain_maps(compact_chain_map(previous.board), compact_chain_map(state.board))
    placed_point = event.point if event and event.kind == "play" else None
    captured_points = event.captures if event else []
    changed_points = sorted(set(([placed_point] if placed_point else []) + captured_points))
    return {
        "event": event.to_dict() if event else None,
        "placed_point": placed_point,
        "captured_points": captured_points,
        "changed_points": changed_points,
        "changed_chain_anchors": diff["changed_chain_anchors"],
        "changed_chains": diff["changed_chains"],
    }


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
        event_number=state.event_number,
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


def restore_snapshot(
    entry: HistoryEntry,
    history: list[HistoryEntry],
    *,
    schema_version: int,
    board_size: int,
    komi: float,
    handicap: int,
) -> GameState:
    return GameState(
        schema_version=schema_version,
        board_size=board_size,
        komi=komi,
        handicap=handicap,
        status=entry.status,
        event_number=entry.event_number,
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
        "event_number": state.event_number,
        "move_number": state.move_number,
        "side_to_move": state.side_to_move,
        "ko_point": state.ko_point,
        "capture_counts": state.capture_counts.to_dict(),
        "last_move": state.last_move.to_dict() if state.last_move else None,
    }


def event_requires_turn(kind: EventKind) -> bool:
    return kind in {"play", "pass", "resign"}


def last_event(state: GameState) -> MoveRecord | None:
    if not state.move_log:
        return None
    return state.move_log[-1]


def set_status(state: GameState, status: GameStatus) -> None:
    state.status = status


def ensure_status(state: GameState, allowed: set[GameStatus], command: str) -> None:
    if state.status not in allowed:
        raise RefereeError(
            "invalid_status_transition",
            f"Command '{command}' is not allowed while status is {state.status}",
            {"status": state.status, "command": command},
        )


def append_event(
    state: GameState,
    *,
    kind: EventKind,
    color: Color | None,
    point: Coord | None,
    captures: list[Coord] | None = None,
    ko_point_after: Coord | None = None,
    reason: str | None = None,
) -> MoveRecord:
    state.event_number += 1
    if event_requires_turn(kind):
        state.move_number += 1
    record = MoveRecord(
        number=state.event_number,
        color=color,
        kind=kind,
        point=point,
        captures=captures or [],
        ko_point_after=ko_point_after,
        reason=reason,
    )
    state.move_log.append(record)
    return record


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
    if state.event_number != len(state.move_log):
        raise RefereeError("move_log", "Event number does not match move log length")
    turn_events = sum(1 for item in state.move_log if event_requires_turn(item.kind))
    if state.move_number != turn_events:
        raise RefereeError("move_log", "Move number does not match turn-event count")
    checks["move_log"] = True
    if state.move_number == 0:
        if state.last_move is not None:
            raise RefereeError("last_move", "Last move must be null at move 0")
    else:
        if state.last_move is None:
            raise RefereeError("last_move", "Last move is missing")
        turn_log = [item for item in state.move_log if event_requires_turn(item.kind)]
        if not turn_log:
            raise RefereeError("last_move", "Last move is missing")
        last_record = turn_log[-1]
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
    valid_status = {"active", "scoring", "finished"}
    if state.status not in valid_status:
        raise RefereeError("status", "Invalid game status", {"status": state.status})
    latest = last_event(state)
    if state.status == "scoring":
        if len(state.move_log) < 2 or state.move_log[-1].kind != "pass" or state.move_log[-2].kind != "pass":
            raise RefereeError("status", "Scoring requires consecutive passes")
    if state.status == "finished":
        if latest is None or latest.kind not in {"resign", "finalize"}:
            raise RefereeError("status", "Finished game must end with resignation or finalization")
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
        or expected.event_number != replayed.event_number
        or expected.move_number != replayed.move_number
        or expected.capture_counts.to_dict() != replayed.capture_counts.to_dict()
        or (expected.last_move.to_dict() if expected.last_move else None)
        != (replayed.last_move.to_dict() if replayed.last_move else None)
    )
    if mismatch:
        raise RefereeError("replay_mismatch", "Stored state does not match replayed move log")


def ensure_active_turn(state: GameState, color: Color) -> None:
    if state.status != "active":
        raise RefereeError(
            "invalid_status_transition",
            f"Command 'play' is not allowed while status is {state.status}",
            {"status": state.status, "command": "play"},
        )
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


def explain_move_legality(state: GameState, color: Color, move: Coord, *, ignore_turn: bool = False) -> dict[str, Any]:
    text = move.upper()
    point = parse_coord(text)
    analysis_state = clone_state(state)
    if ignore_turn:
        analysis_state.side_to_move = color
        analysis_state.status = "active"
    occupied = get_stone(analysis_state.board, point) != "empty"
    legal, reason = is_move_legal(analysis_state, color, text)
    result: dict[str, Any] = {
        "point": text,
        "legal": legal,
        "reason": reason,
        "occupied": occupied,
        "ko_point": analysis_state.ko_point,
        "would_capture": [],
        "would_be_suicide": False,
        "resulting_liberty_count": None,
        "adjacent_enemy_chains_after_capture": [],
    }
    if occupied:
        return result

    board = board_copy(analysis_state.board)
    set_stone(board, point, color_to_stone(color))
    captured_points = find_captures_after_play(board, point, color)
    for captured_point in captured_points:
        set_stone(board, captured_point, "empty")
    result["would_capture"] = sorted(format_coord(item) for item in captured_points)
    try:
        info = chain_info(board, point)
    except RefereeError:
        info = None
    if info is not None:
        result["resulting_liberty_count"] = len(info.liberties)
        result["would_be_suicide"] = len(info.liberties) == 0
    adjacent_enemy: list[dict[str, Any]] = []
    seen_enemy_anchors: set[Coord] = set()
    for neighbor in neighbors(point):
        if get_stone(board, neighbor) != other_color(color):
            continue
        payload = chain_payload(board, chain_info(board, neighbor))
        if payload["anchor"] in seen_enemy_anchors:
            continue
        seen_enemy_anchors.add(payload["anchor"])
        adjacent_enemy.append(
            {
                "anchor": payload["anchor"],
                "stones": payload["stones"],
                "liberties": payload["liberties"],
                "liberty_count": payload["liberty_count"],
                "in_atari": payload["in_atari"],
            }
        )
    adjacent_enemy.sort(key=lambda item: item["anchor"])
    result["adjacent_enemy_chains_after_capture"] = adjacent_enemy
    return result


def simulate_play(state: GameState, color: Color, move: Coord, *, ignore_turn: bool = False) -> dict[str, Any]:
    analysis = explain_move_legality(state, color, move, ignore_turn=ignore_turn)
    result: dict[str, Any] = {
        "color": color,
        "move": move.upper(),
        "legal": analysis["legal"],
        "reason": analysis["reason"],
    }
    if not analysis["legal"]:
        return result
    simulated = clone_state(state)
    if ignore_turn:
        simulated.side_to_move = color
        simulated.status = "active"
    apply_result = apply_play(simulated, color, move.upper())
    played_point = parse_coord(move.upper())
    played_chain = chain_info(simulated.board, played_point)
    result.update(
        {
            "captures": apply_result.captures,
            "capture_count_delta": apply_result.capture_count_delta,
            "ko_point_after": apply_result.ko_point,
            "result_state": state_summary(simulated),
            "played_chain": {
                "anchor": chain_anchor(played_chain.stones),
                "stones": sorted(format_coord(item) for item in played_chain.stones),
                "liberties": sorted(format_coord(item) for item in played_chain.liberties),
                "liberty_count": len(played_chain.liberties),
                "in_atari": len(played_chain.liberties) == 1,
            },
            "board_diff": {
                "placed": [move.upper()],
                "removed": apply_result.captures,
                "changed_points": sorted([move.upper(), *apply_result.captures]),
            },
            "adjacent_enemy_chains_after_play": analysis["adjacent_enemy_chains_after_capture"],
        }
    )
    return result


def parse_sequence_steps(spec: str, *, max_steps: int = 20) -> list[SequenceStep]:
    if not spec.strip():
        raise RefereeError("invalid_sequence", "Sequence must not be empty")
    raw_steps = [item.strip() for item in spec.split(",") if item.strip()]
    if len(raw_steps) > max_steps:
        raise RefereeError(
            "invalid_sequence",
            f"Sequence exceeds maximum length of {max_steps}",
            {"max_steps": max_steps, "count": len(raw_steps)},
        )
    steps: list[SequenceStep] = []
    for raw_step in raw_steps:
        if ":" not in raw_step:
            raise RefereeError("invalid_sequence", f"Invalid sequence token: {raw_step}", {"token": raw_step})
        color_code, action_text = raw_step.split(":", 1)
        color_key = color_code.strip().upper()
        action = action_text.strip().upper()
        if color_key not in {"B", "W"}:
            raise RefereeError("invalid_sequence", f"Invalid sequence token: {raw_step}", {"token": raw_step})
        color: Color = "black" if color_key == "B" else "white"
        if action == "PASS":
            steps.append(SequenceStep(color=color, kind="pass", move=None))
        elif action == "RESIGN":
            steps.append(SequenceStep(color=color, kind="resign", move=None))
        else:
            parse_coord(action)
            steps.append(SequenceStep(color=color, kind="play", move=action))
    return steps


def simulate_sequence(state: GameState, spec: str) -> dict[str, Any]:
    simulated = clone_state(state)
    steps = parse_sequence_steps(spec)
    applied: list[dict[str, Any]] = []
    stopped_early = False
    stop_reason: str | None = None
    for index, step in enumerate(steps, start=1):
        try:
            captures: list[Coord] = []
            if step.kind == "play":
                play_result = apply_play(simulated, step.color, step.move or "")
                captures = play_result.captures
            elif step.kind == "pass":
                apply_pass(simulated, step.color)
            else:
                apply_resign(simulated, step.color)
            applied.append(
                {
                    "index": index,
                    "color": step.color,
                    "kind": step.kind,
                    "move": step.move,
                    "legal": True,
                    "reason": None,
                    "captures": captures,
                }
            )
        except RefereeError as exc:
            applied.append(
                {
                    "index": index,
                    "color": step.color,
                    "kind": step.kind,
                    "move": step.move,
                    "legal": False,
                    "reason": exc.code,
                    "captures": [],
                }
            )
            stopped_early = True
            stop_reason = exc.code
            break
    return {
        "applied": applied,
        "stopped_early": stopped_early,
        "stop_reason": stop_reason,
        "final_state": state_summary(simulated),
        "final_chains": query_board(simulated)["chains"],
    }


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
    captures = sorted(format_coord(item) for item in captured_points)
    record = append_event(
        state,
        kind="play",
        color=color,
        point=move.upper(),
        captures=captures,
        ko_point_after=state.ko_point,
    )
    state.last_move = LastMove.from_record(record)
    state.side_to_move = other_color(color)
    set_status(state, "active")
    return PlayResult(
        applied_move=record,
        captures=captures,
        capture_count_delta=delta,
        ko_point=state.ko_point,
        status=state.status,
        state=state_summary(state),
    )


def apply_pass(state: GameState, color: Color) -> dict[str, Any]:
    ensure_status(state, {"active"}, "pass")
    if color != state.side_to_move:
        raise RefereeError(
            "wrong_side",
            f"It is {state.side_to_move}'s turn",
            {"expected": state.side_to_move, "actual": color},
        )
    previous = snapshot_state(state)
    prior_was_pass = bool(state.move_log) and state.move_log[-1].kind == "pass"
    state.history.append(previous)
    state.ko_point = None
    record = append_event(
        state,
        kind="pass",
        color=color,
        point=None,
        captures=[],
        ko_point_after=None,
    )
    state.last_move = LastMove.from_record(record)
    state.side_to_move = other_color(color)
    set_status(state, "scoring" if prior_was_pass else "active")
    return {"applied_move": record.to_dict(), "status": state.status, "state": state_summary(state)}


def apply_resign(state: GameState, color: Color) -> dict[str, Any]:
    ensure_status(state, {"active"}, "resign")
    if color != state.side_to_move:
        raise RefereeError(
            "wrong_side",
            f"It is {state.side_to_move}'s turn",
            {"expected": state.side_to_move, "actual": color},
        )
    previous = snapshot_state(state)
    state.history.append(previous)
    state.ko_point = None
    record = append_event(
        state,
        kind="resign",
        color=color,
        point=None,
        captures=[],
        ko_point_after=None,
    )
    state.last_move = LastMove.from_record(record)
    set_status(state, "finished")
    winner = other_color(color)
    return {
        "applied_move": record.to_dict(),
        "status": state.status,
        "winner": winner,
        "state": state_summary(state),
    }


def apply_resume(state: GameState) -> dict[str, Any]:
    ensure_status(state, {"scoring"}, "resume")
    previous = snapshot_state(state)
    state.history.append(previous)
    set_status(state, "active")
    record = append_event(
        state,
        kind="resume",
        color=None,
        point=None,
        captures=[],
        ko_point_after=state.ko_point,
        reason="resume_play_after_scoring",
    )
    return {"applied_event": record.to_dict(), "status": state.status, "state": state_summary(state)}


def apply_finalize(state: GameState) -> dict[str, Any]:
    ensure_status(state, {"scoring"}, "finalize")
    previous = snapshot_state(state)
    state.history.append(previous)
    set_status(state, "finished")
    record = append_event(
        state,
        kind="finalize",
        color=None,
        point=None,
        captures=[],
        ko_point_after=state.ko_point,
        reason="finalize_game_after_scoring",
    )
    return {"applied_event": record.to_dict(), "status": state.status, "state": state_summary(state)}


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


def query_point(state: GameState, coord: Coord, *, local_radius: int | None = None) -> dict[str, Any]:
    validate_local_radius(local_radius)
    point = parse_coord(coord)
    occupant = get_stone(state.board, point)
    neighbor_points = neighbors(point)
    neighbor_coords = [format_coord(item) for item in neighbor_points]
    if occupant == "empty":
        friendly_neighbors = {"black": [], "white": []}
        enemy_neighbors = {"black": [], "white": []}
        touching_chain_anchors: dict[str, list[Coord]] = {"black": [], "white": []}
        for color in ("black", "white"):
            friendly_neighbors[color] = sorted(
                format_coord(item) for item in neighbor_points if get_stone(state.board, item) == color
            )
            enemy_neighbors[color] = sorted(
                format_coord(item) for item in neighbor_points if get_stone(state.board, item) == other_color(color)
            )
            touching_chain_anchors[color] = sorted(
                {
                    chain_anchor(chain_info(state.board, item).stones)
                    for item in neighbor_points
                    if get_stone(state.board, item) == color
                }
            )
        chain = None
    else:
        info = chain_info(state.board, point)
        chain = {
            "color": occupant,
            "anchor": chain_anchor(info.stones),
            "stones": sorted(format_coord(item) for item in info.stones),
            "liberties": sorted(format_coord(item) for item in info.liberties),
            "liberty_count": len(info.liberties),
            "in_atari": len(info.liberties) == 1,
        }
        friendly_neighbors = sorted(
            format_coord(item) for item in neighbor_points if get_stone(state.board, item) == occupant
        )
        enemy_neighbors = sorted(
            format_coord(item) for item in neighbor_points if get_stone(state.board, item) == other_color(occupant)
        )
        touching_chain_anchors = {
            "occupied_chain": chain["anchor"],
            "friendly": sorted(
                {
                    chain_anchor(chain_info(state.board, item).stones)
                    for item in neighbor_points
                    if get_stone(state.board, item) == occupant and item not in info.stones
                }
            ),
            "enemy": sorted(
                {
                    chain_anchor(chain_info(state.board, item).stones)
                    for item in neighbor_points
                    if get_stone(state.board, item) == other_color(occupant)
                }
            ),
        }
    move_effects = {}
    for color in ("black", "white"):
        move_analysis = explain_move_legality(state, color, coord.upper(), ignore_turn=True)
        move_effects[color] = {
            "legal": move_analysis["legal"],
            "reason": move_analysis["reason"],
            "captures": move_analysis["would_capture"],
            "self_atari": move_analysis["legal"] and move_analysis["resulting_liberty_count"] == 1,
            "resulting_liberty_count": move_analysis["resulting_liberty_count"] if move_analysis["legal"] else None,
            "ko_point_after": None,
        }
        if move_analysis["legal"]:
            preview = simulate_play(state, color, coord.upper(), ignore_turn=True)
            move_effects[color]["ko_point_after"] = preview["ko_point_after"]
            move_effects[color]["preview"] = {
                "played_chain": preview["played_chain"],
                "board_diff": preview["board_diff"],
                "adjacent_enemy_chains_after_play": preview["adjacent_enemy_chains_after_play"],
                "capture_count_delta": preview["capture_count_delta"],
                "ko_point_after": preview["ko_point_after"],
            }
    payload: dict[str, Any] = {
        "point": coord.upper(),
        "occupant": occupant,
        "neighbors": neighbor_coords,
        "empty_neighbor_count": sum(1 for item in neighbor_points if get_stone(state.board, item) == "empty"),
        "touching_chain_anchors": touching_chain_anchors,
        "move_effects": move_effects,
    }
    if occupant == "empty":
        payload["friendly_neighbors"] = friendly_neighbors
        payload["enemy_neighbors"] = enemy_neighbors
    else:
        payload["friendly_neighbors"] = friendly_neighbors
        payload["enemy_neighbors"] = enemy_neighbors
        payload["chain"] = chain
    if local_radius is not None:
        payload["local_view"] = build_local_view(state, point, local_radius)
    return payload


def query_chain(state: GameState, coord: Coord, *, local_radius: int | None = None) -> dict[str, Any]:
    validate_local_radius(local_radius)
    base = chain_at(state, coord.upper())
    if base["occupant"] == "empty":
        base["in_atari"] = False
        base["chain_anchor"] = None
        base["adjacent_enemy_chains"] = []
        base["adjacent_friendly_chains"] = []
        base["shared_liberties"] = {}
        if local_radius is not None:
            base["local_view"] = build_local_view(state, parse_coord(coord.upper()), local_radius)
        return base
    point = parse_coord(coord.upper())
    info = chain_info(state.board, point)
    own_color = get_stone(state.board, point)
    enemy_payloads: dict[Coord, dict[str, Any]] = {}
    friendly_payloads: dict[Coord, dict[str, Any]] = {}
    for stone in info.stones:
        for neighbor in neighbors(stone):
            stone_color = get_stone(state.board, neighbor)
            if stone_color == "empty":
                continue
            neighbor_info = chain_info(state.board, neighbor)
            anchor = chain_anchor(neighbor_info.stones)
            if neighbor_info.stones == info.stones:
                continue
            payload = {
                "anchor": anchor,
                "stones": sorted(format_coord(item) for item in neighbor_info.stones),
                "liberties": sorted(format_coord(item) for item in neighbor_info.liberties),
                "liberty_count": len(neighbor_info.liberties),
                "in_atari": len(neighbor_info.liberties) == 1,
            }
            if stone_color == own_color:
                friendly_payloads[anchor] = payload
            else:
                enemy_payloads[anchor] = payload
    shared_liberties = {
        anchor: sorted(set(base["liberties"]).intersection(payload["liberties"]))
        for anchor, payload in enemy_payloads.items()
    }
    base["chain_anchor"] = chain_anchor(info.stones)
    base["in_atari"] = base["liberty_count"] == 1
    base["adjacent_enemy_chains"] = [enemy_payloads[key] for key in sorted(enemy_payloads)]
    base["adjacent_friendly_chains"] = [friendly_payloads[key] for key in sorted(friendly_payloads)]
    base["shared_liberties"] = {key: shared_liberties[key] for key in sorted(shared_liberties)}
    if local_radius is not None:
        base["local_view"] = build_local_view(state, point, local_radius)
    return base


def query_board(
    state: GameState,
    *,
    include_last_event: bool = False,
    include_low_liberty: bool = False,
    liberty_threshold: int = 2,
) -> dict[str, Any]:
    validate_liberty_threshold(liberty_threshold)
    chains = enumerate_chains(state.board)
    compact_chains: list[dict[str, Any]] = []
    black_in_atari: list[Coord] = []
    white_in_atari: list[Coord] = []
    for payload in chains:
        anchor = payload["anchor"]
        point = parse_coord(anchor)
        info = chain_info(state.board, point)
        adjacent_enemy_anchors: set[Coord] = set()
        for stone in info.stones:
            for neighbor in neighbors(stone):
                if get_stone(state.board, neighbor) != other_color(payload["color"]):
                    continue
                adjacent_enemy_anchors.add(chain_anchor(chain_info(state.board, neighbor).stones))
        compact = {
            "color": payload["color"],
            "stones": payload["stones"],
            "anchor": anchor,
            "liberties": payload["liberties"],
            "liberty_count": payload["liberty_count"],
            "in_atari": payload["in_atari"],
            "adjacent_enemy_chain_anchors": sorted(adjacent_enemy_anchors),
        }
        compact_chains.append(compact)
        if payload["color"] == "black" and payload["in_atari"]:
            black_in_atari.append(anchor)
        if payload["color"] == "white" and payload["in_atari"]:
            white_in_atari.append(anchor)
    compact_chains.sort(key=lambda item: (item["color"], item["liberty_count"], item["anchor"]))
    payload = {
        "side_to_move": state.side_to_move,
        "status": state.status,
        "ko_point": state.ko_point,
        "capture_counts": state.capture_counts.to_dict(),
        "chain_summary": {
            "black_chain_count": sum(1 for item in compact_chains if item["color"] == "black"),
            "white_chain_count": sum(1 for item in compact_chains if item["color"] == "white"),
            "black_in_atari": sorted(black_in_atari),
            "white_in_atari": sorted(white_in_atari),
        },
        "chains": compact_chains,
        "empty_regions": enumerate_empty_regions(state.board),
    }
    if include_last_event:
        payload["last_event_summary"] = build_last_event_summary(state)
    if include_low_liberty:
        payload["low_liberty_chains"] = [
            {
                "anchor": item["anchor"],
                "color": item["color"],
                "stones": item["stones"],
                "liberties": item["liberties"],
                "liberty_count": item["liberty_count"],
                "in_atari": item["in_atari"],
            }
            for item in compact_chains
            if item["liberty_count"] <= liberty_threshold
        ]
    return payload


def undo(state: GameState, count: int) -> dict[str, Any]:
    if count < 1:
        raise RefereeError("invalid_undo", "Undo count must be at least 1", {"count": count})
    if len(state.history) < count:
        raise RefereeError("invalid_undo", "Not enough history to undo", {"count": count})
    history = state.history[:]
    restored: GameState | None = None
    for _ in range(count):
        snapshot = history.pop()
        restored = restore_snapshot(
            snapshot,
            history[:],
            schema_version=state.schema_version,
            board_size=state.board_size,
            komi=state.komi,
            handicap=state.handicap,
        )
        history = restored.history[:]
    if restored is None:
        raise RefereeError("invalid_undo", "Nothing to undo")
    state.schema_version = restored.schema_version
    state.board_size = restored.board_size
    state.komi = restored.komi
    state.handicap = restored.handicap
    state.status = restored.status
    state.event_number = restored.event_number
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
        if record.number != state.event_number + 1:
            raise RefereeError("move_log", "Event numbers must be sequential")
        if record.kind == "play":
            if record.color is None:
                raise RefereeError("move_log", "Play events require a color")
            apply_play(state, record.color, record.point or "")
        elif record.kind == "pass":
            if record.color is None:
                raise RefereeError("move_log", "Pass events require a color")
            apply_pass(state, record.color)
        elif record.kind == "resign":
            if record.color is None:
                raise RefereeError("move_log", "Resign events require a color")
            apply_resign(state, record.color)
        elif record.kind == "resume":
            apply_resume(state)
        elif record.kind == "finalize":
            apply_finalize(state)
        else:
            raise RefereeError("move_log", "Unknown move kind", {"kind": record.kind})
        replayed_record = state.move_log[-1]
        if replayed_record.kind != record.kind or replayed_record.number != record.number:
            raise RefereeError("move_log", "Stored event does not match replayed event", {"number": record.number})
        if replayed_record.color != record.color or replayed_record.point != record.point:
            raise RefereeError("move_log", "Stored event payload does not match replayed event", {"number": record.number})
        if replayed_record.reason != record.reason:
            raise RefereeError("move_log", "Stored event reason does not match replayed event", {"number": record.number})
    return state
