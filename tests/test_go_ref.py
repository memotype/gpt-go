from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from models import Color, GameState, MoveRecord
from referee import (
    apply_pass,
    apply_play,
    apply_resign,
    chain_at,
    is_move_legal,
    list_legal_moves,
    parse_coord,
    replay_move_log,
    undo,
    validate_state,
)
from render import render_text, validate_rendered_text


REPO_ROOT = Path(__file__).resolve().parent.parent
LEGACY_DIR = REPO_ROOT / "docs" / "legacy-ascii"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "renderer"


def play_sequence(state: GameState, moves: list[tuple[Color, str]]) -> GameState:
    for color, move in moves:
        apply_play(state, color, move)
    return state


def configure_position(
    black_points: list[str],
    white_points: list[str],
    *,
    side_to_move: Color = "black",
    ko_point: str | None = None,
) -> GameState:
    state = GameState.new_game()
    state.side_to_move = side_to_move
    state.ko_point = ko_point
    for coord in black_points:
        x, y = parse_coord(coord)
        state.board[y][x] = "black"
    for coord in white_points:
        x, y = parse_coord(coord)
        state.board[y][x] = "white"
    return state


def extract_legacy_moves() -> list[MoveRecord]:
    text = (LEGACY_DIR / "game-example-manual-v1.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    start = lines.index("========") + 2
    move_log: list[MoveRecord] = []
    for line in lines[start:]:
        if not line.strip():
            continue
        number_text, move_text = line.split(". ", 1)
        move_log.append(
            MoveRecord(
                number=int(number_text),
                color="black" if int(number_text) % 2 == 1 else "white",
                kind="play",
                point=move_text.strip(),
                captures=[],
                ko_point_after=None,
            )
        )
    return move_log


class RefereeRulesTests(unittest.TestCase):
    def test_coordinate_parsing_skips_i(self) -> None:
        self.assertEqual(parse_coord("A1"), (0, 8))
        self.assertEqual(parse_coord("J9"), (8, 0))
        with self.assertRaises(Exception):
            parse_coord("I5")

    def test_single_stone_capture(self) -> None:
        state = GameState.new_game()
        play_sequence(
            state,
            [
                ("black", "B2"),
                ("white", "B1"),
                ("black", "A1"),
                ("white", "A3"),
                ("black", "C1"),
                ("white", "C3"),
                ("black", "B3"),
            ],
        )
        self.assertEqual(state.board[8][1], "empty")
        self.assertEqual(state.capture_counts.black, 1)

    def test_multi_stone_chain_capture(self) -> None:
        state = configure_position(
            black_points=["A2", "B1", "B3", "C1", "C3"],
            white_points=["B2", "C2"],
            side_to_move="black",
        )
        apply_play(state, "black", "D2")
        self.assertEqual(state.board[7][1], "empty")
        self.assertEqual(state.board[7][2], "empty")
        self.assertEqual(state.capture_counts.black, 2)

    def test_multi_chain_capture(self) -> None:
        state = configure_position(
            black_points=["A2", "B1", "B3", "D1", "D3", "E2"],
            white_points=["B2", "D2"],
            side_to_move="black",
        )
        result = apply_play(state, "black", "C2")
        self.assertEqual(sorted(result.captures), ["B2", "D2"])
        self.assertEqual(state.capture_counts.black, 2)

    def test_suicide_is_illegal(self) -> None:
        state = GameState.new_game()
        play_sequence(
            state,
            [
                ("black", "B1"),
                ("white", "J9"),
                ("black", "A2"),
                ("white", "J8"),
                ("black", "B3"),
                ("white", "J7"),
                ("black", "C2"),
            ],
        )
        legal, reason = is_move_legal(state, "white", "B2")
        self.assertFalse(legal)
        self.assertEqual(reason, "suicide")

    def test_suicide_becomes_legal_by_capture(self) -> None:
        state = configure_position(
            black_points=["A1", "A3", "B4", "C1", "C3", "D2"],
            white_points=["A2", "B1", "B3", "C2"],
            side_to_move="black",
        )
        legal, reason = is_move_legal(state, "black", "B2")
        self.assertTrue(legal)
        self.assertIsNone(reason)
        result = apply_play(state, "black", "B2")
        self.assertEqual(sorted(result.captures), ["A2", "B1", "B3", "C2"])

    def test_simple_ko_and_immediate_recapture(self) -> None:
        state = configure_position(
            black_points=["A2", "B1"],
            white_points=["B2", "C1"],
            side_to_move="white",
        )
        result = apply_play(state, "white", "A1")
        self.assertEqual(result.captures, ["B1"])
        self.assertEqual(state.ko_point, "B1")
        legal, reason = is_move_legal(state, "black", "B1")
        self.assertFalse(legal)
        self.assertEqual(reason, "ko")

    def test_pass_pass_ends_game(self) -> None:
        state = GameState.new_game()
        apply_pass(state, "black")
        self.assertEqual(state.status, "passed")
        apply_pass(state, "white")
        self.assertEqual(state.status, "game_over")

    def test_resignation_ends_game(self) -> None:
        state = GameState.new_game()
        result = apply_resign(state, "black")
        self.assertEqual(state.status, "resigned")
        self.assertEqual(result["winner"], "white")

    def test_undo_single_and_multiple(self) -> None:
        state = GameState.new_game()
        play_sequence(state, [("black", "E5"), ("white", "D5"), ("black", "F5")])
        undo(state, 1)
        self.assertEqual(state.move_number, 2)
        undo(state, 2)
        self.assertEqual(state.move_number, 0)
        self.assertEqual(len(state.move_log), 0)

    def test_chain_query(self) -> None:
        state = GameState.new_game()
        play_sequence(state, [("black", "D4"), ("white", "J9"), ("black", "D5"), ("white", "J8"), ("black", "E5")])
        data = chain_at(state, "D4")
        self.assertEqual(sorted(data["chain"]), ["D4", "D5", "E5"])
        self.assertIn("C4", data["liberties"])

    def test_validate_replay_matches_state(self) -> None:
        state = GameState.new_game()
        play_sequence(state, [("black", "E5"), ("white", "C3"), ("black", "A3")])
        checks = validate_state(state)
        self.assertTrue(checks["replay"])

    def test_legal_lists_points_only(self) -> None:
        state = GameState.new_game()
        legal_moves = list_legal_moves(state, "black")
        self.assertEqual(len(legal_moves), 81)
        self.assertEqual(legal_moves[0], "A9")


class RendererTests(unittest.TestCase):
    def assert_board_rows_uniform_width(self, rendered: str) -> None:
        board_rows = [line for line in rendered.splitlines() if line.startswith("  ") and line[2:3].isdigit()]
        self.assertTrue(board_rows)
        self.assertEqual(len({len(row) for row in board_rows}), 1)

    def test_blank_board_matches_legacy_init(self) -> None:
        state = GameState.new_game()
        rendered = render_text(state)
        expected = (LEGACY_DIR / "game-init-manual-v1.txt").read_text(encoding="utf-8")
        self.assertEqual(rendered.rstrip("\n"), expected.rstrip("\n"))

    def test_last_move_parentheses_and_hoshi_rendering(self) -> None:
        state = GameState.new_game()
        apply_play(state, "black", "E5")
        rendered = render_text(state)
        self.assertIn("(X)", rendered)
        self.assertNotIn("+", next(line for line in rendered.splitlines() if line.startswith("  5 ")))
        self.assertIn("  5 . . . .(X). . . . 5", rendered)
        self.assert_board_rows_uniform_width(rendered)

    def test_left_edge_last_move_stays_aligned(self) -> None:
        state = GameState.new_game()
        apply_play(state, "black", "A5")
        rendered = render_text(state)
        self.assertIn("  5(X). . . + . . . . 5", rendered)
        self.assert_board_rows_uniform_width(rendered)

    def test_right_edge_last_move_stays_aligned(self) -> None:
        state = GameState.new_game()
        apply_play(state, "black", "J5")
        rendered = render_text(state)
        self.assertIn("  5 . . . . + . . .(X)5", rendered)
        self.assert_board_rows_uniform_width(rendered)

    def test_no_parentheses_after_pass_and_stale_ko_removal(self) -> None:
        state = configure_position(
            black_points=["A2", "B1"],
            white_points=["B2", "C1"],
            side_to_move="white",
        )
        apply_play(state, "white", "A1")
        self.assertEqual(state.ko_point, "B1")
        apply_pass(state, "black")
        rendered = render_text(state)
        board_rows = [line for line in rendered.splitlines() if line.startswith("  ") and line[2:3].isdigit()]
        self.assertEqual(sum(row.count("(X)") + row.count("(O)") for row in board_rows), 0)
        self.assertNotIn("~", rendered)

    def test_legacy_example_regression(self) -> None:
        move_log = extract_legacy_moves()
        state = replay_move_log(move_log, 6.5, 0)
        rendered = render_text(state)
        expected = (LEGACY_DIR / "game-example-manual-v1.txt").read_text(encoding="utf-8")
        self.assertEqual(rendered.rstrip("\n"), expected.rstrip("\n"))

    def test_validate_rendered_text_rejects_misaligned_rows(self) -> None:
        state = GameState.new_game()
        apply_play(state, "black", "A5")
        rendered = render_text(state)
        broken = rendered.replace("  5(X). . . + . . . . 5", "  5 (X). . . + . . . . 5")
        with self.assertRaisesRegex(ValueError, "uniformly aligned"):
            validate_rendered_text(state, broken)


class CliTests(unittest.TestCase):
    def run_cli(self, cwd: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(REPO_ROOT / "go_ref.py"), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_cli_json_stdout_and_error_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            init = self.run_cli(tmpdir, "init")
            payload = json.loads(init.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(init.stderr, "")

            illegal = self.run_cli(tmpdir, "play", "--color", "white", "--move", "E5", check=False)
            self.assertEqual(illegal.returncode, 1)
            error_payload = json.loads(illegal.stdout)
            self.assertFalse(error_payload["ok"])
            self.assertIn("turn", illegal.stderr)

    def test_cli_renderer_regression_fixtures(self) -> None:
        scenarios = [
            ("a5_last_move", [("black", "A5")]),
            ("a7_last_move", [("black", "A7")]),
            ("e5_last_move", [("black", "E5")]),
            ("j5_last_move", [("black", "J5")]),
        ]
        for fixture_name, moves in scenarios:
            with self.subTest(fixture=fixture_name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    self.run_cli(tmpdir, "init")
                    for color, move in moves:
                        self.run_cli(tmpdir, "play", "--color", color, "--move", move)
                    rendered = Path(tmpdir, "game.txt").read_text(encoding="utf-8")
                    expected = (FIXTURES_DIR / f"{fixture_name}.txt").read_text(encoding="utf-8")
                    self.assertEqual(rendered.rstrip("\n"), expected.rstrip("\n"))


if __name__ == "__main__":
    unittest.main()
