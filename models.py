from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Color = Literal["black", "white"]
GameStatus = Literal["active", "passed", "resigned", "game_over"]
MoveKind = Literal["play", "pass", "resign"]
Stone = Literal["empty", "black", "white"]
Coord = str
Point = tuple[int, int]

SCHEMA_VERSION = 1
BOARD_SIZE = 9
KOMI = 6.5
HANDICAP = 0
COLUMNS = "ABCDEFGHJ"
HOSHI_POINTS: frozenset[Coord] = frozenset({"C7", "G7", "E5", "C3", "G3"})


def empty_coord_list() -> list[Coord]:
    return []


def empty_move_record_list() -> list["MoveRecord"]:
    return []


def empty_history_entry_list() -> list["HistoryEntry"]:
    return []


@dataclass(slots=True)
class CaptureCounts:
    black: int = 0
    white: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaptureCounts":
        return cls(black=int(data["black"]), white=int(data["white"]))

    def to_dict(self) -> dict[str, int]:
        return {"black": self.black, "white": self.white}


@dataclass(slots=True)
class MoveRecord:
    number: int
    color: Color
    kind: MoveKind
    point: Coord | None
    captures: list[Coord] = field(default_factory=empty_coord_list)
    ko_point_after: Coord | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MoveRecord":
        return cls(
            number=int(data["number"]),
            color=data["color"],
            kind=data["kind"],
            point=data.get("point"),
            captures=list(data.get("captures", [])),
            ko_point_after=data.get("ko_point_after"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LastMove:
    color: Color
    kind: MoveKind
    point: Coord | None

    @classmethod
    def from_record(cls, record: MoveRecord) -> "LastMove":
        return cls(color=record.color, kind=record.kind, point=record.point)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LastMove":
        return cls(color=data["color"], kind=data["kind"], point=data.get("point"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HistoryEntry:
    move_number: int
    position_hash: str
    board: list[list[Stone]]
    ko_point: Coord | None
    capture_counts: CaptureCounts
    side_to_move: Color
    status: GameStatus
    last_move: LastMove | None
    move_log: list[MoveRecord]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryEntry":
        return cls(
            move_number=int(data["move_number"]),
            position_hash=data["position_hash"],
            board=[[cell for cell in row] for row in data["board"]],
            ko_point=data.get("ko_point"),
            capture_counts=CaptureCounts.from_dict(data["capture_counts"]),
            side_to_move=data["side_to_move"],
            status=data["status"],
            last_move=LastMove.from_dict(data["last_move"]) if data.get("last_move") else None,
            move_log=[MoveRecord.from_dict(item) for item in data.get("move_log", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "move_number": self.move_number,
            "position_hash": self.position_hash,
            "board": self.board,
            "ko_point": self.ko_point,
            "capture_counts": self.capture_counts.to_dict(),
            "side_to_move": self.side_to_move,
            "status": self.status,
            "last_move": self.last_move.to_dict() if self.last_move else None,
            "move_log": [move.to_dict() for move in self.move_log],
        }


@dataclass(slots=True)
class GameState:
    schema_version: int
    board_size: int
    komi: float
    handicap: int
    status: GameStatus
    move_number: int
    side_to_move: Color
    ko_point: Coord | None
    capture_counts: CaptureCounts
    last_move: LastMove | None
    board: list[list[Stone]]
    move_log: list[MoveRecord] = field(default_factory=empty_move_record_list)
    history: list[HistoryEntry] = field(default_factory=empty_history_entry_list)

    @classmethod
    def new_game(cls) -> "GameState":
        return cls(
            schema_version=SCHEMA_VERSION,
            board_size=BOARD_SIZE,
            komi=KOMI,
            handicap=HANDICAP,
            status="active",
            move_number=0,
            side_to_move="black",
            ko_point=None,
            capture_counts=CaptureCounts(),
            last_move=None,
            board=[["empty" for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)],
            move_log=[],
            history=[],
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameState":
        return cls(
            schema_version=int(data["schema_version"]),
            board_size=int(data["board_size"]),
            komi=float(data["komi"]),
            handicap=int(data["handicap"]),
            status=data["status"],
            move_number=int(data["move_number"]),
            side_to_move=data["side_to_move"],
            ko_point=data.get("ko_point"),
            capture_counts=CaptureCounts.from_dict(data["capture_counts"]),
            last_move=LastMove.from_dict(data["last_move"]) if data.get("last_move") else None,
            board=[[cell for cell in row] for row in data["board"]],
            move_log=[MoveRecord.from_dict(item) for item in data.get("move_log", [])],
            history=[HistoryEntry.from_dict(item) for item in data.get("history", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "board_size": self.board_size,
            "komi": self.komi,
            "handicap": self.handicap,
            "status": self.status,
            "move_number": self.move_number,
            "side_to_move": self.side_to_move,
            "ko_point": self.ko_point,
            "capture_counts": self.capture_counts.to_dict(),
            "last_move": self.last_move.to_dict() if self.last_move else None,
            "board": self.board,
            "move_log": [move.to_dict() for move in self.move_log],
            "history": [entry.to_dict() for entry in self.history],
        }


@dataclass(slots=True)
class ChainInfo:
    stones: set[Point]
    liberties: set[Point]
