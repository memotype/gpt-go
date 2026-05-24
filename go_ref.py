from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from models import Color, GameState
from referee import (
    RefereeError,
    apply_pass,
    apply_play,
    apply_resign,
    chain_at,
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


def emit(payload: dict[str, Any], exit_code: int = 0) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


def success(command: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "state_path": str(STATE_PATH),
        "game_path": str(GAME_PATH),
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


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="go_ref", description="9x9 Go referee")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")
    subparsers.add_parser("show")

    play = subparsers.add_parser("play")
    play.add_argument("--color", required=True, choices=["black", "white"])
    play.add_argument("--move", required=True)

    passed = subparsers.add_parser("pass")
    passed.add_argument("--color", required=True, choices=["black", "white"])

    resign = subparsers.add_parser("resign")
    resign.add_argument("--color", required=True, choices=["black", "white"])

    legal = subparsers.add_parser("legal")
    legal.add_argument("--color", required=True, choices=["black", "white"])
    legal.add_argument("--move")

    chain = subparsers.add_parser("chain")
    chain.add_argument("--point", required=True)

    subparsers.add_parser("validate")
    subparsers.add_parser("render")

    undo_parser = subparsers.add_parser("undo")
    undo_parser.add_argument("--count", type=int, default=1)

    return parser


def parse_color(value: str) -> Color:
    if value not in {"black", "white"}:
        raise RefereeError("invalid_color", f"Invalid color: {value}", {"color": value})
    return cast(Color, value)


def init_command() -> dict[str, Any]:
    state = GameState.new_game()
    save_state(STATE_PATH, state)
    render_to_path(state, GAME_PATH)
    return {"created": True, "state": state_summary(state)}


def show_command() -> dict[str, Any]:
    state = load_state(STATE_PATH)
    return {"state": state.to_dict()}


def play_command(color: Color, move: str) -> dict[str, Any]:
    state = load_state(STATE_PATH)
    result = apply_play(state, color, move.upper())
    save_state(STATE_PATH, state)
    render_to_path(state, GAME_PATH)
    return {
        "applied_move": result.applied_move.to_dict(),
        "captures": result.captures,
        "capture_count_delta": result.capture_count_delta,
        "ko_point": result.ko_point,
        "status": result.status,
        "state": result.state,
    }


def pass_command(color: Color) -> dict[str, Any]:
    state = load_state(STATE_PATH)
    result = apply_pass(state, color)
    save_state(STATE_PATH, state)
    render_to_path(state, GAME_PATH)
    return result


def resign_command(color: Color) -> dict[str, Any]:
    state = load_state(STATE_PATH)
    result = apply_resign(state, color)
    save_state(STATE_PATH, state)
    render_to_path(state, GAME_PATH)
    return result


def legal_command(color: Color, move: str | None) -> dict[str, Any]:
    state = load_state(STATE_PATH)
    if move is not None:
        legal, reason = is_move_legal(state, color, move.upper())
        return {"color": color, "move": move.upper(), "legal": legal, "reason": reason}
    legal_moves = list_legal_moves(state, color)
    return {
        "color": color,
        "legal_moves": legal_moves,
        "pass_legal": state.status not in {"resigned", "game_over"} and state.side_to_move == color,
        "count": len(legal_moves),
        "ko_point": state.ko_point,
    }


def chain_command(point: str) -> dict[str, Any]:
    state = load_state(STATE_PATH)
    return chain_at(state, point.upper())


def validate_command() -> dict[str, Any]:
    state = load_state(STATE_PATH)
    checks = validate_state(state)
    render_to_path(state, GAME_PATH)
    return {"valid": True, "checks": checks}


def render_command() -> dict[str, Any]:
    state = load_state(STATE_PATH)
    render_to_path(state, GAME_PATH)
    return {"rendered": True, "game_path": str(GAME_PATH)}


def undo_command(count: int) -> dict[str, Any]:
    state = load_state(STATE_PATH)
    result = undo(state, count)
    save_state(STATE_PATH, state)
    render_to_path(state, GAME_PATH)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    command = args.command
    try:
        if command == "init":
            result = init_command()
        elif command == "show":
            result = show_command()
        elif command == "play":
            result = play_command(parse_color(args.color), args.move)
        elif command == "pass":
            result = pass_command(parse_color(args.color))
        elif command == "resign":
            result = resign_command(parse_color(args.color))
        elif command == "legal":
            result = legal_command(parse_color(args.color), args.move)
        elif command == "chain":
            result = chain_command(args.point)
        elif command == "validate":
            result = validate_command()
        elif command == "render":
            result = render_command()
        elif command == "undo":
            result = undo_command(args.count)
        else:
            raise RefereeError("unknown_command", "Unknown command", {"command": command})
        return emit(success(command, result))
    except RefereeError as error:
        print(f"{command}: {error.message}", file=sys.stderr)
        return emit(failure(command, error), exit_code=1)
    except Exception as error:  # pragma: no cover
        print(f"{command}: unexpected error: {error}", file=sys.stderr)
        wrapped = RefereeError("internal_error", str(error))
        return emit(failure(command, wrapped), exit_code=1)


if __name__ == "__main__":
    raise SystemExit(main())
