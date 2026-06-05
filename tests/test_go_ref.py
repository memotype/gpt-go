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
    explain_move_legality,
    is_move_legal,
    list_legal_moves,
    parse_coord,
    query_board,
    query_chain,
    query_point,
    replay_move_log,
    simulate_play,
    simulate_sequence,
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


class TacticalQueryTests(unittest.TestCase):
    def test_query_point_on_empty_reports_move_effects_for_both_colors(self) -> None:
        state = configure_position(
            black_points=["B1", "A2", "B3", "C2"],
            white_points=[],
            side_to_move="white",
        )
        data = query_point(state, "B2")
        self.assertEqual(data["occupant"], "empty")
        self.assertEqual(data["empty_neighbor_count"], 0)
        self.assertFalse(data["move_effects"]["white"]["legal"])
        self.assertEqual(data["move_effects"]["white"]["reason"], "suicide")
        self.assertTrue(data["move_effects"]["black"]["legal"])
        self.assertEqual(data["move_effects"]["black"]["resulting_liberty_count"], 6)

    def test_query_chain_reports_adjacencies_and_shared_liberties(self) -> None:
        state = configure_position(
            black_points=["D4", "D5"],
            white_points=["C4", "E4", "D3"],
            side_to_move="black",
        )
        data = query_chain(state, "D4")
        self.assertEqual(data["chain"], ["D4", "D5"])
        self.assertFalse(data["in_atari"])
        self.assertEqual(len(data["adjacent_enemy_chains"]), 3)
        self.assertEqual(sorted(data["shared_liberties"].keys()), ["C4", "D3", "E4"])
        self.assertEqual(data["shared_liberties"]["D3"], [])

    def test_query_board_summarizes_chains_and_empty_regions(self) -> None:
        state = configure_position(
            black_points=["A1", "A2", "J9"],
            white_points=["B1", "J8"],
            side_to_move="black",
        )
        data = query_board(state)
        self.assertEqual(data["chain_summary"]["black_chain_count"], 2)
        self.assertEqual(data["chain_summary"]["white_chain_count"], 2)
        self.assertEqual(data["chains"][0]["anchor"], "J9")
        self.assertTrue(data["empty_regions"])
        self.assertIn("black", data["empty_regions"][0]["bordering_colors"])

    def test_try_play_matches_capture_result_without_mutating_state(self) -> None:
        state = configure_position(
            black_points=["A2", "B1", "B3", "C1", "C3"],
            white_points=["B2", "C2"],
            side_to_move="black",
        )
        before = state.to_dict()
        data = simulate_play(state, "black", "D2")
        self.assertTrue(data["legal"])
        self.assertEqual(data["captures"], ["B2", "C2"])
        self.assertEqual(data["board_diff"]["changed_points"], ["B2", "C2", "D2"])
        self.assertEqual(state.to_dict(), before)

    def test_try_play_illegal_reports_reason(self) -> None:
        state = configure_position(
            black_points=["A2", "B1", "B3", "C2"],
            white_points=[],
            side_to_move="white",
        )
        data = simulate_play(state, "white", "B2")
        self.assertFalse(data["legal"])
        self.assertEqual(data["reason"], "suicide")

    def test_try_legality_reports_local_evidence(self) -> None:
        state = configure_position(
            black_points=["A1", "A3", "B4", "C1", "C3", "D2"],
            white_points=["A2", "B1", "B3", "C2"],
            side_to_move="black",
        )
        data = explain_move_legality(state, "black", "B2")
        self.assertTrue(data["legal"])
        self.assertEqual(data["would_capture"], ["A2", "B1", "B3", "C2"])
        self.assertFalse(data["would_be_suicide"])
        self.assertEqual(data["resulting_liberty_count"], 4)

    def test_try_sequence_stops_on_first_illegal_step(self) -> None:
        state = GameState.new_game()
        data = simulate_sequence(state, "B:E5,W:E5,B:D5")
        self.assertTrue(data["stopped_early"])
        self.assertEqual(data["stop_reason"], "illegal_move")
        self.assertEqual(len(data["applied"]), 2)
        self.assertTrue(data["applied"][0]["legal"])
        self.assertFalse(data["applied"][1]["legal"])
        self.assertEqual(data["final_state"]["move_number"], 1)

    def test_try_sequence_supports_pass_and_resign(self) -> None:
        state = GameState.new_game()
        data = simulate_sequence(state, "B:pass,W:resign")
        self.assertFalse(data["stopped_early"])
        self.assertEqual(data["final_state"]["status"], "resigned")
        self.assertEqual(data["final_state"]["move_number"], 2)


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

    def test_cli_query_and_try_commands_return_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "init")
            self.run_cli(tmpdir, "play", "--color", "black", "--move", "E5")
            point_payload = json.loads(self.run_cli(tmpdir, "query", "point", "--point", "E4").stdout)
            self.assertTrue(point_payload["ok"])
            self.assertEqual(point_payload["result"]["point"], "E4")

            chain_payload = json.loads(self.run_cli(tmpdir, "query", "chain", "--point", "E5").stdout)
            self.assertTrue(chain_payload["ok"])
            self.assertEqual(chain_payload["result"]["occupant"], "black")

            board_payload = json.loads(self.run_cli(tmpdir, "query", "board").stdout)
            self.assertTrue(board_payload["ok"])
            self.assertIn("chains", board_payload["result"])

            try_play_payload = json.loads(
                self.run_cli(tmpdir, "try", "play", "--color", "white", "--move", "D5").stdout
            )
            self.assertTrue(try_play_payload["ok"])
            self.assertTrue(try_play_payload["result"]["legal"])

            try_legality_payload = json.loads(
                self.run_cli(tmpdir, "try", "legality", "--color", "white", "--move", "E5").stdout
            )
            self.assertTrue(try_legality_payload["ok"])
            self.assertFalse(try_legality_payload["result"]["legal"])

            try_sequence_payload = json.loads(
                self.run_cli(tmpdir, "try", "sequence", "--moves", "W:D5,B:C3").stdout
            )
            self.assertTrue(try_sequence_payload["ok"])
            self.assertFalse(try_sequence_payload["result"]["stopped_early"])

    def test_cli_query_and_try_do_not_mutate_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "init")
            self.run_cli(tmpdir, "play", "--color", "black", "--move", "E5")
            state_before = Path(tmpdir, "state.json").read_text(encoding="utf-8")
            game_before = Path(tmpdir, "game.txt").read_text(encoding="utf-8")

            commands = [
                ("query", "point", "--point", "E4"),
                ("query", "chain", "--point", "E5"),
                ("query", "board"),
                ("try", "play", "--color", "white", "--move", "D5"),
                ("try", "legality", "--color", "white", "--move", "E5"),
                ("try", "sequence", "--moves", "W:D5,B:C3"),
            ]
            for command in commands:
                with self.subTest(command=command):
                    self.run_cli(tmpdir, *command)
                    self.assertEqual(Path(tmpdir, "state.json").read_text(encoding="utf-8"), state_before)
                    self.assertEqual(Path(tmpdir, "game.txt").read_text(encoding="utf-8"), game_before)

    def test_branch_lifecycle_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "init")
            self.run_cli(tmpdir, "play", "--color", "black", "--move", "E5")

            created = json.loads(self.run_cli(tmpdir, "branch", "create", "--name", "semeai-1").stdout)
            self.assertTrue(created["ok"])
            self.assertEqual(created["result"]["name"], "semeai-1")
            self.assertEqual(created["result"]["source"], {"kind": "canonical", "branch_name": None})
            self.assertTrue(created["state_path"].endswith("analysis/branches/semeai-1/state.json"))
            self.assertTrue(created["game_path"].endswith("analysis/branches/semeai-1/game.txt"))

            listed = json.loads(self.run_cli(tmpdir, "branch", "list").stdout)
            self.assertTrue(listed["ok"])
            self.assertEqual([branch["name"] for branch in listed["result"]["branches"]], ["semeai-1"])

            shown = json.loads(self.run_cli(tmpdir, "branch", "show", "--name", "semeai-1").stdout)
            self.assertTrue(shown["ok"])
            self.assertEqual(shown["result"]["state"]["move_number"], 1)

            child = json.loads(
                self.run_cli(tmpdir, "branch", "create", "--name", "ko-read", "--from-branch", "semeai-1").stdout
            )
            self.assertTrue(child["ok"])
            self.assertEqual(child["result"]["source"], {"kind": "branch", "branch_name": "semeai-1"})

            deleted = json.loads(self.run_cli(tmpdir, "branch", "delete", "--name", "ko-read").stdout)
            self.assertTrue(deleted["ok"])
            self.assertEqual(deleted["result"]["name"], "ko-read")
            self.assertFalse(Path(tmpdir, "analysis/branches/ko-read").exists())

    def test_branch_targeted_play_show_query_and_try_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "init")
            self.run_cli(tmpdir, "play", "--color", "black", "--move", "E5")
            self.run_cli(tmpdir, "branch", "create", "--name", "center")

            canonical_state_before = Path(tmpdir, "state.json").read_text(encoding="utf-8")
            canonical_game_before = Path(tmpdir, "game.txt").read_text(encoding="utf-8")

            played = json.loads(
                self.run_cli(tmpdir, "play", "--branch", "center", "--color", "white", "--move", "D5").stdout
            )
            self.assertTrue(played["ok"])
            self.assertTrue(played["state_path"].endswith("analysis/branches/center/state.json"))

            branch_show = json.loads(self.run_cli(tmpdir, "show", "--branch", "center").stdout)
            self.assertEqual(branch_show["result"]["state"]["move_number"], 2)

            canonical_show = json.loads(self.run_cli(tmpdir, "show").stdout)
            self.assertEqual(canonical_show["result"]["state"]["move_number"], 1)

            branch_query = json.loads(self.run_cli(tmpdir, "query", "board", "--branch", "center").stdout)
            self.assertTrue(branch_query["ok"])
            self.assertEqual(branch_query["result"]["side_to_move"], "black")

            branch_try = json.loads(
                self.run_cli(tmpdir, "try", "sequence", "--branch", "center", "--moves", "B:C3,W:C4").stdout
            )
            self.assertTrue(branch_try["ok"])
            self.assertEqual(branch_try["result"]["final_state"]["move_number"], 4)

            self.assertEqual(Path(tmpdir, "state.json").read_text(encoding="utf-8"), canonical_state_before)
            self.assertEqual(Path(tmpdir, "game.txt").read_text(encoding="utf-8"), canonical_game_before)

    def test_branch_reset_and_undo_only_affect_target_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "init")
            self.run_cli(tmpdir, "play", "--color", "black", "--move", "E5")
            self.run_cli(tmpdir, "branch", "create", "--name", "a")
            self.run_cli(tmpdir, "branch", "create", "--name", "b")
            self.run_cli(tmpdir, "play", "--branch", "a", "--color", "white", "--move", "D5")
            self.run_cli(tmpdir, "play", "--branch", "b", "--color", "white", "--move", "C3")

            self.run_cli(tmpdir, "undo", "--branch", "a")
            shown_a = json.loads(self.run_cli(tmpdir, "show", "--branch", "a").stdout)
            shown_b = json.loads(self.run_cli(tmpdir, "show", "--branch", "b").stdout)
            shown_canonical = json.loads(self.run_cli(tmpdir, "show").stdout)
            self.assertEqual(shown_a["result"]["state"]["move_number"], 1)
            self.assertEqual(shown_b["result"]["state"]["move_number"], 2)
            self.assertEqual(shown_canonical["result"]["state"]["move_number"], 1)

            self.run_cli(tmpdir, "branch", "reset", "--name", "b", "--from", "branch", "--source", "a")
            reset_b = json.loads(self.run_cli(tmpdir, "show", "--branch", "b").stdout)
            self.assertEqual(reset_b["result"]["state"]["move_number"], 1)

            self.run_cli(tmpdir, "branch", "reset", "--name", "a", "--from", "canonical")
            reset_a = json.loads(self.run_cli(tmpdir, "show", "--branch", "a").stdout)
            self.assertEqual(reset_a["result"]["state"]["move_number"], 1)

    def test_branch_invalid_and_missing_cases_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "init")

            invalid = self.run_cli(tmpdir, "branch", "create", "--name", "Bad Name", check=False)
            self.assertEqual(invalid.returncode, 1)
            self.assertFalse(json.loads(invalid.stdout)["ok"])

            self.run_cli(tmpdir, "branch", "create", "--name", "readout")
            duplicate = self.run_cli(tmpdir, "branch", "create", "--name", "readout", check=False)
            self.assertEqual(duplicate.returncode, 1)
            self.assertFalse(json.loads(duplicate.stdout)["ok"])

            missing_show = self.run_cli(tmpdir, "branch", "show", "--name", "missing", check=False)
            self.assertEqual(missing_show.returncode, 1)
            self.assertFalse(json.loads(missing_show.stdout)["ok"])

            missing_delete = self.run_cli(tmpdir, "branch", "delete", "--name", "missing", check=False)
            self.assertEqual(missing_delete.returncode, 1)
            self.assertFalse(json.loads(missing_delete.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
