from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, cast

from models import Color, GameState
from referee import (
    RefereeError,
    apply_pass,
    apply_play,
    apply_resign,
    chain_at,
    explain_move_legality,
    parse_sequence_steps,
    query_board,
    query_chain,
    query_point,
    simulate_play,
    simulate_sequence,
    list_legal_moves,
    load_state,
    save_state,
    state_summary,
    undo,
    validate_state,
    is_move_legal,
)
from render import render_to_path

STATE_PATH = Path("state.json")
GAME_PATH = Path("game.txt")
BRANCHES_ROOT = Path("analysis/branches")
BRANCH_NAME_PATTERN = re.compile(r"^[a-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class Target:
    kind: str
    name: str | None
    state_path: Path
    game_path: Path


def emit(payload: dict[str, Any], exit_code: int = 0) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


def success(command: str, result: dict[str, Any], target: Target | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "state_path": str(target.state_path) if target else None,
        "game_path": str(target.game_path) if target else None,
        "result": result,
    }


def failure(command: str, error: RefereeError) -> dict[str, Any]:
    return {
        "ok": False,
        "command": command,
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
        },
    }


def add_branch_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--branch")


def validate_branch_name(name: str) -> str:
    if not BRANCH_NAME_PATTERN.fullmatch(name):
        raise RefereeError("invalid_branch_name", f"Invalid branch name: {name}", {"branch": name})
    return name


def resolve_target(branch_name: str | None) -> Target:
    if branch_name is None:
        return Target(kind="canonical", name=None, state_path=STATE_PATH, game_path=GAME_PATH)
    name = validate_branch_name(branch_name)
    branch_dir = BRANCHES_ROOT / name
    target = Target(kind="branch", name=name, state_path=branch_dir / "state.json", game_path=branch_dir / "game.txt")
    if not target.state_path.exists():
        raise RefereeError("branch_not_found", f"Branch not found: {name}", {"branch": name})
    return target


def branch_target(name: str) -> Target:
    valid_name = validate_branch_name(name)
    branch_dir = BRANCHES_ROOT / valid_name
    return Target(
        kind="branch",
        name=valid_name,
        state_path=branch_dir / "state.json",
        game_path=branch_dir / "game.txt",
    )


def ensure_branch_missing(name: str) -> Target:
    target = branch_target(name)
    if target.state_path.exists() or target.game_path.exists() or target.state_path.parent.exists():
        raise RefereeError("branch_exists", f"Branch already exists: {target.name}", {"branch": target.name})
    return target


def ensure_branch_exists(name: str) -> Target:
    target = branch_target(name)
    if not target.state_path.exists():
        raise RefereeError("branch_not_found", f"Branch not found: {target.name}", {"branch": target.name})
    return target


def load_target_state(target: Target) -> GameState:
    return load_state(target.state_path)


def save_target_state(target: Target, state: GameState) -> None:
    target.state_path.parent.mkdir(parents=True, exist_ok=True)
    save_state(target.state_path, state)


def render_target(target: Target, state: GameState) -> None:
    target.game_path.parent.mkdir(parents=True, exist_ok=True)
    render_to_path(state, target.game_path)


def lock_path_for_target(target: Target) -> Path:
    if target.kind == "canonical":
        return target.state_path.with_name(f".{target.state_path.name}.lock")
    branch_name = target.name or "branch"
    BRANCHES_ROOT.mkdir(parents=True, exist_ok=True)
    return BRANCHES_ROOT / f".{branch_name}.lock"


@contextlib.contextmanager
def locked_targets(*targets: Target) -> Iterator[None]:
    unique_targets = {
        str(target.state_path.resolve()): target
        for target in targets
    }
    lock_files = []
    try:
        for target in sorted(unique_targets.values(), key=lambda item: str(item.state_path.resolve())):
            lock_path = lock_path_for_target(target)
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = lock_path.open("a+", encoding="utf-8")
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            lock_files.append(handle)
        yield
    finally:
        for handle in reversed(lock_files):
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()


def target_summary(target: Target, state: GameState) -> dict[str, Any]:
    return {
        "name": target.name,
        "target_kind": target.kind,
        "state_path": str(target.state_path),
        "game_path": str(target.game_path),
        "state": state_summary(state),
    }


def copy_target_state(source: Target, destination: Target) -> GameState:
    state = load_target_state(source)
    save_target_state(destination, state)
    render_target(destination, state)
    return state


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="go_ref", description="9x9 Go referee")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")
    show = subparsers.add_parser("show")
    add_branch_argument(show)

    play = subparsers.add_parser("play")
    play.add_argument("--color", required=True, choices=["black", "white"])
    play.add_argument("--move", required=True)
    add_branch_argument(play)

    passed = subparsers.add_parser("pass")
    passed.add_argument("--color", required=True, choices=["black", "white"])
    add_branch_argument(passed)

    resign = subparsers.add_parser("resign")
    resign.add_argument("--color", required=True, choices=["black", "white"])
    add_branch_argument(resign)

    legal = subparsers.add_parser("legal")
    legal.add_argument("--color", required=True, choices=["black", "white"])
    legal.add_argument("--move")
    add_branch_argument(legal)

    chain = subparsers.add_parser("chain")
    chain.add_argument("--point", required=True)
    add_branch_argument(chain)

    query = subparsers.add_parser("query")
    query_subparsers = query.add_subparsers(dest="query_command", required=True)

    query_point_parser = query_subparsers.add_parser("point")
    query_point_parser.add_argument("--point", required=True)
    add_branch_argument(query_point_parser)

    query_chain_parser = query_subparsers.add_parser("chain")
    query_chain_parser.add_argument("--point", required=True)
    add_branch_argument(query_chain_parser)

    query_board_parser = query_subparsers.add_parser("board")
    add_branch_argument(query_board_parser)

    try_parser = subparsers.add_parser("try")
    try_subparsers = try_parser.add_subparsers(dest="try_command", required=True)

    try_play_parser = try_subparsers.add_parser("play")
    try_play_parser.add_argument("--color", required=True, choices=["black", "white"])
    try_play_parser.add_argument("--move", required=True)
    add_branch_argument(try_play_parser)

    try_legality_parser = try_subparsers.add_parser("legality")
    try_legality_parser.add_argument("--color", required=True, choices=["black", "white"])
    try_legality_parser.add_argument("--move", required=True)
    add_branch_argument(try_legality_parser)

    try_sequence_parser = try_subparsers.add_parser("sequence")
    try_sequence_parser.add_argument("--moves", required=True)
    add_branch_argument(try_sequence_parser)

    branch = subparsers.add_parser("branch")
    branch_subparsers = branch.add_subparsers(dest="branch_command", required=True)

    branch_create = branch_subparsers.add_parser("create")
    branch_create.add_argument("--name", required=True)
    branch_create.add_argument("--from-branch")

    branch_subparsers.add_parser("list")

    branch_show = branch_subparsers.add_parser("show")
    branch_show.add_argument("--name", required=True)

    branch_delete = branch_subparsers.add_parser("delete")
    branch_delete.add_argument("--name", required=True)

    branch_reset = branch_subparsers.add_parser("reset")
    branch_reset.add_argument("--name", required=True)
    branch_reset.add_argument("--from", dest="reset_from", required=True, choices=["canonical", "branch"])
    branch_reset.add_argument("--source")

    validate = subparsers.add_parser("validate")
    add_branch_argument(validate)
    render = subparsers.add_parser("render")
    add_branch_argument(render)

    undo_parser = subparsers.add_parser("undo")
    undo_parser.add_argument("--count", type=int, default=1)
    add_branch_argument(undo_parser)

    return parser


def parse_color(value: str) -> Color:
    if value not in {"black", "white"}:
        raise RefereeError("invalid_color", f"Invalid color: {value}", {"color": value})
    return cast(Color, value)


def init_command() -> tuple[dict[str, Any], Target]:
    target = resolve_target(None)
    state = GameState.new_game()
    save_target_state(target, state)
    render_target(target, state)
    return ({"created": True, "state": state_summary(state)}, target)


def show_command(target: Target) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    return ({"state": state.to_dict()}, target)


def play_command(target: Target, color: Color, move: str) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    result = apply_play(state, color, move.upper())
    save_target_state(target, state)
    render_target(target, state)
    return (
        {
            "applied_move": result.applied_move.to_dict(),
            "captures": result.captures,
            "capture_count_delta": result.capture_count_delta,
            "ko_point": result.ko_point,
            "status": result.status,
            "state": result.state,
        },
        target,
    )


def pass_command(target: Target, color: Color) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    result = apply_pass(state, color)
    save_target_state(target, state)
    render_target(target, state)
    return (result, target)


def resign_command(target: Target, color: Color) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    result = apply_resign(state, color)
    save_target_state(target, state)
    render_target(target, state)
    return (result, target)


def legal_command(target: Target, color: Color, move: str | None) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    if move is not None:
        legal, reason = is_move_legal(state, color, move.upper())
        return ({"color": color, "move": move.upper(), "legal": legal, "reason": reason}, target)
    legal_moves = list_legal_moves(state, color)
    return (
        {
            "color": color,
            "legal_moves": legal_moves,
            "pass_legal": state.status not in {"resigned", "game_over"} and state.side_to_move == color,
            "count": len(legal_moves),
            "ko_point": state.ko_point,
        },
        target,
    )


def chain_command(target: Target, point: str) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    return (chain_at(state, point.upper()), target)


def validate_command(target: Target) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    checks = validate_state(state)
    render_target(target, state)
    return ({"valid": True, "checks": checks}, target)


def render_command(target: Target) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    render_target(target, state)
    return ({"rendered": True, "game_path": str(target.game_path)}, target)


def undo_command(target: Target, count: int) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    result = undo(state, count)
    save_target_state(target, state)
    render_target(target, state)
    return (result, target)


def query_point_command(target: Target, point: str) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    return (query_point(state, point.upper()), target)


def query_chain_command(target: Target, point: str) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    return (query_chain(state, point.upper()), target)


def query_board_command(target: Target) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    return (query_board(state), target)


def try_play_command(target: Target, color: Color, move: str) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    return (simulate_play(state, color, move.upper()), target)


def try_legality_command(target: Target, color: Color, move: str) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    return (explain_move_legality(state, color, move.upper()), target)


def try_sequence_command(target: Target, moves: str) -> tuple[dict[str, Any], Target]:
    state = load_target_state(target)
    parse_sequence_steps(moves)
    return (simulate_sequence(state, moves), target)


def branch_create_command(name: str, from_branch: str | None) -> tuple[dict[str, Any], Target]:
    target = ensure_branch_missing(name)
    source = resolve_target(from_branch)
    state = copy_target_state(source, target)
    return (
        {
            "name": target.name,
            "created": True,
            "source": {"kind": source.kind, "branch_name": source.name},
            "state": state_summary(state),
        },
        target,
    )


def branch_list_command() -> tuple[dict[str, Any], None]:
    branches: list[dict[str, Any]] = []
    if BRANCHES_ROOT.exists():
        for branch_dir in sorted(item for item in BRANCHES_ROOT.iterdir() if item.is_dir()):
            name = branch_dir.name
            try:
                target = ensure_branch_exists(name)
                state = load_target_state(target)
            except RefereeError:
                continue
            branches.append(
                {
                    "name": name,
                    "state_path": str(target.state_path),
                    "game_path": str(target.game_path),
                    "move_number": state.move_number,
                    "side_to_move": state.side_to_move,
                    "status": state.status,
                    "last_move": state.last_move.to_dict() if state.last_move else None,
                }
            )
    return ({"branches": branches}, None)


def branch_show_command(name: str) -> tuple[dict[str, Any], Target]:
    target = ensure_branch_exists(name)
    state = load_target_state(target)
    return ({"name": target.name, "state": state.to_dict()}, target)


def branch_delete_command(name: str) -> tuple[dict[str, Any], Target]:
    target = ensure_branch_exists(name)
    shutil.rmtree(target.state_path.parent)
    return ({"name": target.name, "deleted": True}, target)


def branch_reset_command(name: str, reset_from: str, source_name: str | None) -> tuple[dict[str, Any], Target]:
    target = ensure_branch_exists(name)
    if reset_from == "canonical":
        if source_name is not None:
            raise RefereeError("invalid_branch_reset", "Canonical reset does not take --source", {"branch": name})
        source = resolve_target(None)
    else:
        if source_name is None:
            raise RefereeError("invalid_branch_reset", "Branch reset requires --source", {"branch": name})
        source = ensure_branch_exists(source_name)
    state = copy_target_state(source, target)
    return (
        {
            "name": target.name,
            "reset_from": {"kind": source.kind, "branch_name": source.name},
            "state": state_summary(state),
        },
        target,
    )


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    command = args.command
    try:
        if command == "init":
            target = resolve_target(None)
            with locked_targets(target):
                result, target = init_command()
        elif command == "show":
            target = resolve_target(args.branch)
            with locked_targets(target):
                result, target = show_command(target)
        elif command == "play":
            target = resolve_target(args.branch)
            with locked_targets(target):
                result, target = play_command(target, parse_color(args.color), args.move)
        elif command == "pass":
            target = resolve_target(args.branch)
            with locked_targets(target):
                result, target = pass_command(target, parse_color(args.color))
        elif command == "resign":
            target = resolve_target(args.branch)
            with locked_targets(target):
                result, target = resign_command(target, parse_color(args.color))
        elif command == "legal":
            target = resolve_target(args.branch)
            with locked_targets(target):
                result, target = legal_command(target, parse_color(args.color), args.move)
        elif command == "chain":
            target = resolve_target(args.branch)
            with locked_targets(target):
                result, target = chain_command(target, args.point)
        elif command == "query":
            if args.query_command == "point":
                target = resolve_target(args.branch)
                with locked_targets(target):
                    result, target = query_point_command(target, args.point)
            elif args.query_command == "chain":
                target = resolve_target(args.branch)
                with locked_targets(target):
                    result, target = query_chain_command(target, args.point)
            elif args.query_command == "board":
                target = resolve_target(args.branch)
                with locked_targets(target):
                    result, target = query_board_command(target)
            else:
                raise RefereeError("unknown_command", "Unknown query command", {"command": args.query_command})
        elif command == "try":
            if args.try_command == "play":
                target = resolve_target(args.branch)
                with locked_targets(target):
                    result, target = try_play_command(target, parse_color(args.color), args.move)
            elif args.try_command == "legality":
                target = resolve_target(args.branch)
                with locked_targets(target):
                    result, target = try_legality_command(target, parse_color(args.color), args.move)
            elif args.try_command == "sequence":
                target = resolve_target(args.branch)
                with locked_targets(target):
                    result, target = try_sequence_command(target, args.moves)
            else:
                raise RefereeError("unknown_command", "Unknown try command", {"command": args.try_command})
        elif command == "branch":
            if args.branch_command == "create":
                destination = branch_target(args.name)
                source = resolve_target(args.from_branch)
                with locked_targets(source, destination):
                    result, target = branch_create_command(args.name, args.from_branch)
            elif args.branch_command == "list":
                result, target = branch_list_command()
            elif args.branch_command == "show":
                target = ensure_branch_exists(args.name)
                with locked_targets(target):
                    result, target = branch_show_command(args.name)
            elif args.branch_command == "delete":
                target = ensure_branch_exists(args.name)
                with locked_targets(target):
                    result, target = branch_delete_command(args.name)
            elif args.branch_command == "reset":
                destination = ensure_branch_exists(args.name)
                if args.reset_from == "canonical":
                    source = resolve_target(None)
                else:
                    if args.source is None:
                        raise RefereeError("invalid_branch_reset", "Branch reset requires --source", {"branch": args.name})
                    source = ensure_branch_exists(args.source)
                with locked_targets(source, destination):
                    result, target = branch_reset_command(args.name, args.reset_from, args.source)
            else:
                raise RefereeError("unknown_command", "Unknown branch command", {"command": args.branch_command})
        elif command == "validate":
            target = resolve_target(args.branch)
            with locked_targets(target):
                result, target = validate_command(target)
        elif command == "render":
            target = resolve_target(args.branch)
            with locked_targets(target):
                result, target = render_command(target)
        elif command == "undo":
            target = resolve_target(args.branch)
            with locked_targets(target):
                result, target = undo_command(target, args.count)
        else:
            raise RefereeError("unknown_command", "Unknown command", {"command": command})
        return emit(success(command, result, target))
    except RefereeError as error:
        print(f"{command}: {error.message}", file=sys.stderr)
        return emit(failure(command, error), exit_code=1)
    except Exception as error:  # pragma: no cover
        print(f"{command}: unexpected error: {error}", file=sys.stderr)
        wrapped = RefereeError("internal_error", str(error))
        return emit(failure(command, wrapped), exit_code=1)


if __name__ == "__main__":
    raise SystemExit(main())
