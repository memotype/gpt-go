from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import shutil
import sys
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO, TypedDict, cast

from models import Color, GameState
from referee import (
    RefereeError,
    apply_pass,
    apply_play,
    apply_resign,
    chain_at,
    load_state,
    query_board,
    query_chain,
    query_point,
    save_state,
    state_summary,
    undo,
    validate_state,
    is_move_legal,
    list_legal_moves,
)
from render import render_to_path

STATE_PATH = Path("state.json")
GAME_PATH = Path("game.txt")
SESSIONS_ROOT = Path("analysis/sessions")
SESSION_NAME_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-")


class ErrorPayload(TypedDict):
    code: str
    message: str
    details: dict[str, object]


class MetaPayload(TypedDict):
    name: str
    kind: str
    base: dict[str, object]
    created_at: str
    updated_at: str


class TargetPayload(TypedDict):
    kind: str
    name: str | None
    state_path: str
    game_path: str
    meta_path: str | None


class SuccessPayload(TypedDict):
    ok: bool
    command: str
    result: dict[str, object]


class FailurePayload(TypedDict):
    ok: bool
    command: str
    error: ErrorPayload


@dataclass(frozen=True, slots=True)
class Target:
    kind: str
    name: str | None
    state_path: Path
    game_path: Path
    meta_path: Path | None = None


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def emit(payload: SuccessPayload | FailurePayload, exit_code: int = 0) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


def success(command: str, result: dict[str, object]) -> SuccessPayload:
    return {"ok": True, "command": command, "result": result}


def failure(command: str, error: RefereeError) -> FailurePayload:
    return {
        "ok": False,
        "command": command,
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
        },
    }


def validate_session_name(name: str) -> str:
    if not name or any(char not in SESSION_NAME_CHARS for char in name):
        raise RefereeError("invalid_session_name", f"Invalid session name: {name}", {"session": name})
    return name


def game_target() -> Target:
    return Target(kind="game", name=None, state_path=STATE_PATH, game_path=GAME_PATH)


def session_target(name: str) -> Target:
    valid_name = validate_session_name(name)
    session_dir = SESSIONS_ROOT / valid_name
    return Target(
        kind="session",
        name=valid_name,
        state_path=session_dir / "state.json",
        game_path=session_dir / "game.txt",
        meta_path=session_dir / "meta.json",
    )


def ensure_session_exists(name: str) -> Target:
    target = session_target(name)
    if not target.state_path.exists() or target.meta_path is None or not target.meta_path.exists():
        raise RefereeError("session_not_found", f"Session not found: {name}", {"session": name})
    return target


def ensure_session_missing(name: str) -> Target:
    target = session_target(name)
    if target.state_path.exists() or (target.meta_path is not None and target.meta_path.exists()):
        raise RefereeError("session_exists", f"Session already exists: {name}", {"session": name})
    return target


def target_payload(target: Target) -> TargetPayload:
    return {
        "kind": target.kind,
        "name": target.name,
        "state_path": str(target.state_path),
        "game_path": str(target.game_path),
        "meta_path": str(target.meta_path) if target.meta_path else None,
    }


def load_target_state(target: Target) -> GameState:
    return load_state(target.state_path)


def save_target_state(target: Target, state: GameState) -> None:
    target.state_path.parent.mkdir(parents=True, exist_ok=True)
    save_state(target.state_path, state)


def render_target(target: Target, state: GameState) -> None:
    target.game_path.parent.mkdir(parents=True, exist_ok=True)
    render_to_path(state, target.game_path)


def load_session_meta(target: Target) -> MetaPayload:
    if target.meta_path is None or not target.meta_path.exists():
        raise RefereeError("session_meta_missing", f"Session metadata missing for {target.name}", {"session": target.name})
    try:
        return cast(MetaPayload, json.loads(target.meta_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise RefereeError("invalid_json", f"Invalid JSON in {target.meta_path}: {exc.msg}") from exc


def save_session_meta(target: Target, meta: MetaPayload) -> None:
    if target.meta_path is None:
        raise RefereeError("session_meta_missing", "Session target is missing meta path")
    target.meta_path.parent.mkdir(parents=True, exist_ok=True)
    target.meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def session_meta_payload(meta: MetaPayload) -> dict[str, object]:
    return {
        "name": meta["name"],
        "kind": meta["kind"],
        "base": meta["base"],
        "created_at": meta["created_at"],
        "updated_at": meta["updated_at"],
    }


def source_payload(kind: str, name: str | None = None) -> dict[str, object]:
    if kind == "game":
        return {"kind": "game", "name": None, "ref": "game"}
    return {"kind": "session", "name": name, "ref": f"session:{name}"}


def parse_source_spec(spec: str) -> Target:
    text = spec.strip()
    if text == "game":
        return game_target()
    prefix = "session:"
    if text.startswith(prefix):
        return ensure_session_exists(text[len(prefix) :])
    raise RefereeError("invalid_source", f"Invalid source: {spec}", {"source": spec})


def copy_target_state(source: Target, destination: Target) -> GameState:
    state = load_target_state(source)
    save_target_state(destination, state)
    render_target(destination, state)
    return state


def copy_session(target: Target, source: Target, *, kind: str) -> dict[str, object]:
    state = copy_target_state(source, target)
    timestamp = now_iso()
    meta: MetaPayload = {
        "name": cast(str, target.name),
        "kind": kind,
        "base": source_payload(source.kind, source.name),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    save_session_meta(target, meta)
    return {"target": target_payload(target), "session": session_meta_payload(meta), "state": state_summary(state)}


def touch_session_meta(target: Target) -> None:
    meta = load_session_meta(target)
    meta["updated_at"] = now_iso()
    save_session_meta(target, meta)


def lock_path_for_target(target: Target) -> Path:
    if target.kind == "game":
        return target.state_path.with_name(f".{target.state_path.name}.lock")
    session_name = target.name or "session"
    SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
    return SESSIONS_ROOT / f".{session_name}.lock"


@contextlib.contextmanager
def locked_targets(*targets: Target) -> Generator[None, None, None]:
    unique_targets = {str(target.state_path.resolve()): target for target in targets}
    lock_files: list[TextIO] = []
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


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="go_ref", description="9x9 Go referee")
    subparsers = root.add_subparsers(dest="command", required=True)

    game = subparsers.add_parser("game")
    game_subparsers = game.add_subparsers(dest="game_command", required=True)

    _ = game_subparsers.add_parser("init")
    _ = game_subparsers.add_parser("show")

    for name in ("play", "pass", "resign", "legal"):
        parser_obj = game_subparsers.add_parser(name)
        _ = parser_obj.add_argument("--color", required=True, choices=["black", "white"])
        if name == "play":
            _ = parser_obj.add_argument("--move", required=True)
        if name == "legal":
            _ = parser_obj.add_argument("--move")

    chain_parser = game_subparsers.add_parser("chain")
    _ = chain_parser.add_argument("--point", required=True)

    query_parser = game_subparsers.add_parser("query")
    query_subparsers = query_parser.add_subparsers(dest="query_command", required=True)
    query_point_parser = query_subparsers.add_parser("point")
    _ = query_point_parser.add_argument("--point", required=True)
    query_chain_parser = query_subparsers.add_parser("chain")
    _ = query_chain_parser.add_argument("--point", required=True)
    _ = query_subparsers.add_parser("board")

    _ = game_subparsers.add_parser("validate")
    _ = game_subparsers.add_parser("render")
    undo_parser = game_subparsers.add_parser("undo")
    _ = undo_parser.add_argument("--count", type=int, default=1)

    session = subparsers.add_parser("session")
    session_subparsers = session.add_subparsers(dest="session_command", required=True)

    create_parser = session_subparsers.add_parser("create")
    _ = create_parser.add_argument("--name", required=True)
    _ = create_parser.add_argument("--from", dest="source", default="game")

    temp_parser = session_subparsers.add_parser("temp")
    _ = temp_parser.add_argument("--from", dest="source", default="game")

    _ = session_subparsers.add_parser("list")

    for name in ("show", "delete", "validate", "render"):
        parser_obj = session_subparsers.add_parser(name)
        _ = parser_obj.add_argument("--name", required=True)

    persist_parser = session_subparsers.add_parser("persist")
    _ = persist_parser.add_argument("--name", required=True)
    _ = persist_parser.add_argument("--as", dest="new_name", required=True)

    reset_parser = session_subparsers.add_parser("reset")
    _ = reset_parser.add_argument("--name", required=True)
    _ = reset_parser.add_argument("--from", dest="source", required=True)

    for name in ("play", "pass", "resign", "legal", "chain", "undo"):
        parser_obj = session_subparsers.add_parser(name)
        _ = parser_obj.add_argument("--name", required=True)
        if name in {"play", "pass", "resign", "legal"}:
            _ = parser_obj.add_argument("--color", required=True, choices=["black", "white"])
        if name == "play":
            _ = parser_obj.add_argument("--move", required=True)
        if name == "legal":
            _ = parser_obj.add_argument("--move")
        if name == "chain":
            _ = parser_obj.add_argument("--point", required=True)
        if name == "undo":
            _ = parser_obj.add_argument("--count", type=int, default=1)

    session_query_parser = session_subparsers.add_parser("query")
    _ = session_query_parser.add_argument("--name", required=True)
    session_query_subparsers = session_query_parser.add_subparsers(dest="query_command", required=True)
    session_query_point = session_query_subparsers.add_parser("point")
    _ = session_query_point.add_argument("--point", required=True)
    session_query_chain = session_query_subparsers.add_parser("chain")
    _ = session_query_chain.add_argument("--point", required=True)
    _ = session_query_subparsers.add_parser("board")

    return root


def parse_color(value: str) -> Color:
    if value not in {"black", "white"}:
        raise RefereeError("invalid_color", f"Invalid color: {value}", {"color": value})
    return cast(Color, value)


def init_game_command() -> dict[str, object]:
    target = game_target()
    state = GameState.new_game()
    save_target_state(target, state)
    render_target(target, state)
    return {"target": target_payload(target), "created": True, "state": state_summary(state)}


def show_command(target: Target) -> dict[str, object]:
    state = load_target_state(target)
    result: dict[str, object] = {"target": target_payload(target), "mutated": False, "state": state.to_dict()}
    if target.kind == "session":
        result["session"] = session_meta_payload(load_session_meta(target))
    return result


def play_command(target: Target, color: Color, move: str) -> dict[str, object]:
    state = load_target_state(target)
    result = apply_play(state, color, move.upper())
    save_target_state(target, state)
    render_target(target, state)
    if target.kind == "session":
        touch_session_meta(target)
    return {
        "target": target_payload(target),
        "mutated": True,
        "applied_move": result.applied_move.to_dict(),
        "captures": result.captures,
        "capture_count_delta": result.capture_count_delta,
        "ko_point": result.ko_point,
        "status": result.status,
        "state": result.state,
    }


def pass_command(target: Target, color: Color) -> dict[str, object]:
    state = load_target_state(target)
    result = apply_pass(state, color)
    save_target_state(target, state)
    render_target(target, state)
    if target.kind == "session":
        touch_session_meta(target)
    return {"target": target_payload(target), "mutated": True, **result}


def resign_command(target: Target, color: Color) -> dict[str, object]:
    state = load_target_state(target)
    result = apply_resign(state, color)
    save_target_state(target, state)
    render_target(target, state)
    if target.kind == "session":
        touch_session_meta(target)
    return {"target": target_payload(target), "mutated": True, **result}


def legal_command(target: Target, color: Color, move: str | None) -> dict[str, object]:
    state = load_target_state(target)
    if move is not None:
        legal, reason = is_move_legal(state, color, move.upper())
        return {
            "target": target_payload(target),
            "mutated": False,
            "color": color,
            "move": move.upper(),
            "legal": legal,
            "reason": reason,
        }
    legal_moves = list_legal_moves(state, color)
    return {
        "target": target_payload(target),
        "mutated": False,
        "color": color,
        "legal_moves": legal_moves,
        "pass_legal": state.status not in {"resigned", "game_over"} and state.side_to_move == color,
        "count": len(legal_moves),
        "ko_point": state.ko_point,
    }


def chain_command(target: Target, point: str) -> dict[str, object]:
    state = load_target_state(target)
    return {"target": target_payload(target), "mutated": False, **chain_at(state, point.upper())}


def validate_command(target: Target) -> dict[str, object]:
    state = load_target_state(target)
    checks = validate_state(state)
    render_target(target, state)
    if target.kind == "session":
        touch_session_meta(target)
    return {"target": target_payload(target), "mutated": False, "valid": True, "checks": checks}


def render_command(target: Target) -> dict[str, object]:
    state = load_target_state(target)
    render_target(target, state)
    if target.kind == "session":
        touch_session_meta(target)
    return {"target": target_payload(target), "mutated": False, "rendered": True}


def undo_command(target: Target, count: int) -> dict[str, object]:
    state = load_target_state(target)
    result = undo(state, count)
    save_target_state(target, state)
    render_target(target, state)
    if target.kind == "session":
        touch_session_meta(target)
    return {"target": target_payload(target), "mutated": True, **result}


def query_point_command(target: Target, point: str) -> dict[str, object]:
    state = load_target_state(target)
    return {"target": target_payload(target), "mutated": False, **query_point(state, point.upper())}


def query_chain_command(target: Target, point: str) -> dict[str, object]:
    state = load_target_state(target)
    return {"target": target_payload(target), "mutated": False, **query_chain(state, point.upper())}


def query_board_command(target: Target) -> dict[str, object]:
    state = load_target_state(target)
    return {"target": target_payload(target), "mutated": False, **query_board(state)}


def session_create_command(name: str, source_spec: str, *, kind: str) -> dict[str, object]:
    destination = ensure_session_missing(name)
    source = parse_source_spec(source_spec)
    return copy_session(destination, source, kind=kind)


def session_temp_name() -> str:
    return f"_tmp_{uuid.uuid4().hex[:8]}"


def session_list_command() -> dict[str, object]:
    sessions: list[dict[str, object]] = []
    if SESSIONS_ROOT.exists():
        for session_dir in sorted(item for item in SESSIONS_ROOT.iterdir() if item.is_dir()):
            try:
                target = ensure_session_exists(session_dir.name)
                state = load_target_state(target)
                meta = load_session_meta(target)
            except RefereeError:
                continue
            sessions.append(
                {
                    "target": target_payload(target),
                    "session": session_meta_payload(meta),
                    "state": state_summary(state),
                }
            )
    return {
        "target": {"kind": "session_collection", "name": None, "state_path": "", "game_path": "", "meta_path": None},
        "mutated": False,
        "sessions": sessions,
    }


def session_delete_command(name: str) -> dict[str, object]:
    target = ensure_session_exists(name)
    meta = load_session_meta(target)
    shutil.rmtree(target.state_path.parent)
    return {"target": target_payload(target), "session": session_meta_payload(meta), "deleted": True}


def session_reset_command(name: str, source_spec: str) -> dict[str, object]:
    target = ensure_session_exists(name)
    source = parse_source_spec(source_spec)
    state = copy_target_state(source, target)
    meta = load_session_meta(target)
    meta["base"] = source_payload(source.kind, source.name)
    meta["updated_at"] = now_iso()
    save_session_meta(target, meta)
    return {
        "target": target_payload(target),
        "session": session_meta_payload(meta),
        "source": source_payload(source.kind, source.name),
        "state": state_summary(state),
    }


def session_persist_command(name: str, new_name: str) -> dict[str, object]:
    source = ensure_session_exists(name)
    destination = ensure_session_missing(new_name)
    state = copy_target_state(source, destination)
    source_meta = load_session_meta(source)
    meta: MetaPayload = {
        "name": cast(str, destination.name),
        "kind": "persistent",
        "base": source_meta["base"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    save_session_meta(destination, meta)
    return {
        "target": target_payload(destination),
        "source": target_payload(source),
        "session": session_meta_payload(meta),
        "state": state_summary(state),
    }


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    command = cast(str, args.command)
    try:
        if command == "game":
            target = game_target()
            with locked_targets(target):
                game_command = cast(str, args.game_command)
                if game_command == "init":
                    result = init_game_command()
                elif game_command == "show":
                    result = show_command(target)
                elif game_command == "play":
                    result = play_command(target, parse_color(cast(str, args.color)), cast(str, args.move))
                elif game_command == "pass":
                    result = pass_command(target, parse_color(cast(str, args.color)))
                elif game_command == "resign":
                    result = resign_command(target, parse_color(cast(str, args.color)))
                elif game_command == "legal":
                    result = legal_command(target, parse_color(cast(str, args.color)), cast(str | None, args.move))
                elif game_command == "chain":
                    result = chain_command(target, cast(str, args.point))
                elif game_command == "query":
                    query_command = cast(str, args.query_command)
                    if query_command == "point":
                        result = query_point_command(target, cast(str, args.point))
                    elif query_command == "chain":
                        result = query_chain_command(target, cast(str, args.point))
                    elif query_command == "board":
                        result = query_board_command(target)
                    else:
                        raise RefereeError("unknown_command", "Unknown game query command", {"command": query_command})
                elif game_command == "validate":
                    result = validate_command(target)
                elif game_command == "render":
                    result = render_command(target)
                elif game_command == "undo":
                    result = undo_command(target, cast(int, args.count))
                else:
                    raise RefereeError("unknown_command", "Unknown game command", {"command": game_command})
        elif command == "session":
            session_command = cast(str, args.session_command)
            if session_command == "create":
                destination = session_target(cast(str, args.name))
                source = parse_source_spec(cast(str, args.source))
                with locked_targets(source, destination):
                    result = session_create_command(cast(str, args.name), cast(str, args.source), kind="persistent")
            elif session_command == "temp":
                temp_name = session_temp_name()
                destination = session_target(temp_name)
                source = parse_source_spec(cast(str, args.source))
                with locked_targets(source, destination):
                    result = session_create_command(temp_name, cast(str, args.source), kind="ephemeral")
            elif session_command == "list":
                result = session_list_command()
            elif session_command == "delete":
                target = ensure_session_exists(cast(str, args.name))
                with locked_targets(target):
                    result = session_delete_command(cast(str, args.name))
            elif session_command == "persist":
                source = ensure_session_exists(cast(str, args.name))
                destination = session_target(cast(str, args.new_name))
                with locked_targets(source, destination):
                    result = session_persist_command(cast(str, args.name), cast(str, args.new_name))
            elif session_command == "reset":
                destination = ensure_session_exists(cast(str, args.name))
                source = parse_source_spec(cast(str, args.source))
                with locked_targets(source, destination):
                    result = session_reset_command(cast(str, args.name), cast(str, args.source))
            else:
                target = ensure_session_exists(cast(str, args.name))
                with locked_targets(target):
                    if session_command == "show":
                        result = show_command(target)
                    elif session_command == "play":
                        result = play_command(target, parse_color(cast(str, args.color)), cast(str, args.move))
                    elif session_command == "pass":
                        result = pass_command(target, parse_color(cast(str, args.color)))
                    elif session_command == "resign":
                        result = resign_command(target, parse_color(cast(str, args.color)))
                    elif session_command == "legal":
                        result = legal_command(target, parse_color(cast(str, args.color)), cast(str | None, args.move))
                    elif session_command == "chain":
                        result = chain_command(target, cast(str, args.point))
                    elif session_command == "query":
                        query_command = cast(str, args.query_command)
                        if query_command == "point":
                            result = query_point_command(target, cast(str, args.point))
                        elif query_command == "chain":
                            result = query_chain_command(target, cast(str, args.point))
                        elif query_command == "board":
                            result = query_board_command(target)
                        else:
                            raise RefereeError(
                                "unknown_command",
                                "Unknown session query command",
                                {"command": query_command},
                            )
                    elif session_command == "validate":
                        result = validate_command(target)
                    elif session_command == "render":
                        result = render_command(target)
                    elif session_command == "undo":
                        result = undo_command(target, cast(int, args.count))
                    else:
                        raise RefereeError("unknown_command", "Unknown session command", {"command": session_command})
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
