from __future__ import annotations

import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from models import Color, GameState, MoveRecord
from referee import (
    apply_finalize,
    apply_pass,
    apply_play,
    apply_resume,
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


def read_lock_queue_ticket(path: Path) -> int:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return 0
    payload = json.loads(raw)
    next_ticket = payload.get("next_ticket", 0)
    if not isinstance(next_ticket, int):
        raise AssertionError(f"Invalid queued lock state at {path}")
    return next_ticket


def wait_for_lock_queue(path: Path, *, minimum_next_ticket: int, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            next_ticket = read_lock_queue_ticket(path)
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.01)
            continue
        if next_ticket >= minimum_next_ticket:
            return
        time.sleep(0.01)
    raise AssertionError(f"Timed out waiting for queued lock state at {path}")


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

    def test_pass_pass_enters_scoring(self) -> None:
        state = GameState.new_game()
        apply_pass(state, "black")
        self.assertEqual(state.status, "active")
        apply_pass(state, "white")
        self.assertEqual(state.status, "scoring")
        self.assertEqual([event.kind for event in state.move_log], ["pass", "pass"])

    def test_resignation_ends_game(self) -> None:
        state = GameState.new_game()
        result = apply_resign(state, "black")
        self.assertEqual(state.status, "finished")
        self.assertEqual(result["winner"], "white")

    def test_resume_preserves_pass_history_and_side_to_move(self) -> None:
        state = GameState.new_game()
        apply_pass(state, "black")
        apply_pass(state, "white")
        board_before = state.to_dict()["board"]
        captures_before = state.capture_counts.to_dict()
        ko_before = state.ko_point

        result = apply_resume(state)

        self.assertEqual(state.status, "active")
        self.assertEqual(state.side_to_move, "black")
        self.assertEqual(state.board, board_before)
        self.assertEqual(state.capture_counts.to_dict(), captures_before)
        self.assertEqual(state.ko_point, ko_before)
        self.assertEqual([event.kind for event in state.move_log], ["pass", "pass", "resume"])
        self.assertEqual(result["applied_event"]["reason"], "resume_play_after_scoring")

    def test_finalize_marks_finished(self) -> None:
        state = GameState.new_game()
        apply_pass(state, "black")
        apply_pass(state, "white")

        result = apply_finalize(state)

        self.assertEqual(state.status, "finished")
        self.assertEqual(state.move_log[-1].kind, "finalize")
        self.assertEqual(result["applied_event"]["reason"], "finalize_game_after_scoring")

    def test_undo_single_and_multiple(self) -> None:
        state = GameState.new_game()
        play_sequence(state, [("black", "E5"), ("white", "D5"), ("black", "F5")])
        undo(state, 1)
        self.assertEqual(state.move_number, 2)
        undo(state, 2)
        self.assertEqual(state.move_number, 0)
        self.assertEqual(len(state.move_log), 0)

    def test_undo_around_scoring_resume_and_finalize(self) -> None:
        state = GameState.new_game()
        apply_pass(state, "black")
        apply_pass(state, "white")
        apply_resume(state)
        self.assertEqual(state.status, "active")
        undo(state, 1)
        self.assertEqual(state.status, "scoring")
        apply_finalize(state)
        self.assertEqual(state.status, "finished")
        undo(state, 1)
        self.assertEqual(state.status, "scoring")

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
        self.assertEqual(data["final_state"]["status"], "finished")
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
        self.assertIn("Status:       Active", rendered)
        self.assertIn("Last event: Black E5", rendered)
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
        self.assertIn("Last event: Black pass", rendered)
        board_rows = [line for line in rendered.splitlines() if line.startswith("  ") and line[2:3].isdigit()]
        self.assertEqual(sum(row.count("(X)") + row.count("(O)") for row in board_rows), 0)
        self.assertNotIn("~", rendered)

    def test_render_shows_scoring_and_finished_statuses(self) -> None:
        state = GameState.new_game()
        apply_pass(state, "black")
        apply_pass(state, "white")
        rendered = render_text(state)
        self.assertIn("Status:       Scoring", rendered)
        self.assertIn("Last event: White pass", rendered)

        apply_finalize(state)
        finalized = render_text(state)
        self.assertIn("Status:       Finished", finalized)
        self.assertIn("Last event: Finalize game after scoring", finalized)

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
            init = self.run_cli(tmpdir, "game", "init")
            payload = json.loads(init.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(init.stderr, "")

            illegal = self.run_cli(tmpdir, "game", "play", "--color", "white", "--move", "E5", check=False)
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
                    self.run_cli(tmpdir, "game", "init")
                    for color, move in moves:
                        self.run_cli(tmpdir, "game", "play", "--color", color, "--move", move)
                    rendered = Path(tmpdir, "game.txt").read_text(encoding="utf-8")
                    expected = (FIXTURES_DIR / f"{fixture_name}.txt").read_text(encoding="utf-8")
                    self.assertEqual(rendered.rstrip("\n"), expected.rstrip("\n"))

    def test_game_query_commands_return_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")
            point_payload = json.loads(self.run_cli(tmpdir, "game", "query", "point", "--point", "E4").stdout)
            self.assertTrue(point_payload["ok"])
            self.assertEqual(point_payload["result"]["point"], "E4")
            self.assertEqual(point_payload["result"]["target"]["kind"], "game")

            chain_payload = json.loads(self.run_cli(tmpdir, "game", "query", "chain", "--point", "E5").stdout)
            self.assertTrue(chain_payload["ok"])
            self.assertEqual(chain_payload["result"]["occupant"], "black")

            board_payload = json.loads(self.run_cli(tmpdir, "game", "query", "board").stdout)
            self.assertTrue(board_payload["ok"])
            self.assertIn("chains", board_payload["result"])

    def test_cli_contract_exposes_target_and_mutated_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            init_payload = json.loads(self.run_cli(tmpdir, "game", "init").stdout)
            self.assertTrue(init_payload["ok"])
            self.assertEqual(init_payload["result"]["target"]["kind"], "game")

            show_payload = json.loads(self.run_cli(tmpdir, "game", "show").stdout)
            self.assertFalse(show_payload["result"]["mutated"])
            self.assertEqual(show_payload["result"]["target"]["kind"], "game")

            play_payload = json.loads(self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5").stdout)
            self.assertTrue(play_payload["result"]["mutated"])
            self.assertEqual(play_payload["result"]["target"]["kind"], "game")

            list_payload = json.loads(self.run_cli(tmpdir, "session", "list").stdout)
            self.assertFalse(list_payload["result"]["mutated"])
            self.assertEqual(list_payload["result"]["target"]["kind"], "session_collection")

    def test_game_queries_do_not_mutate_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")
            state_before = Path(tmpdir, "state.json").read_text(encoding="utf-8")
            game_before = Path(tmpdir, "game.txt").read_text(encoding="utf-8")

            commands = [
                ("game", "query", "point", "--point", "E4"),
                ("game", "query", "chain", "--point", "E5"),
                ("game", "query", "board"),
                ("game", "legal", "--color", "white", "--move", "D5"),
            ]
            for command in commands:
                with self.subTest(command=command):
                    self.run_cli(tmpdir, *command)
                    self.assertEqual(Path(tmpdir, "state.json").read_text(encoding="utf-8"), state_before)
                    self.assertEqual(Path(tmpdir, "game.txt").read_text(encoding="utf-8"), game_before)

    def test_game_scoring_resume_finalize_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")

            first_pass = json.loads(self.run_cli(tmpdir, "game", "pass", "--color", "black").stdout)
            self.assertEqual(first_pass["result"]["status"], "active")

            second_pass = json.loads(self.run_cli(tmpdir, "game", "pass", "--color", "white").stdout)
            self.assertEqual(second_pass["result"]["status"], "scoring")

            shown = json.loads(self.run_cli(tmpdir, "game", "show").stdout)
            self.assertEqual([event["kind"] for event in shown["result"]["state"]["move_log"]], ["pass", "pass"])
            self.assertEqual(shown["result"]["state"]["side_to_move"], "black")

            blocked_play = json.loads(
                self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5", check=False).stdout
            )
            self.assertFalse(blocked_play["ok"])
            self.assertEqual(blocked_play["error"]["code"], "invalid_status_transition")

            legal = json.loads(self.run_cli(tmpdir, "game", "legal", "--color", "black").stdout)
            self.assertEqual(legal["result"]["status"], "scoring")
            self.assertEqual(legal["result"]["legal_moves"], [])
            self.assertFalse(legal["result"]["pass_legal"])

            resumed = json.loads(self.run_cli(tmpdir, "game", "resume").stdout)
            self.assertEqual(resumed["result"]["status"], "active")
            self.assertEqual(resumed["result"]["applied_event"]["kind"], "resume")
            self.assertEqual(resumed["result"]["applied_event"]["reason"], "resume_play_after_scoring")

            played = json.loads(self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5").stdout)
            self.assertTrue(played["ok"])
            self.assertEqual(played["result"]["state"]["move_number"], 3)

            self.run_cli(tmpdir, "game", "undo")
            self.run_cli(tmpdir, "game", "pass", "--color", "black")
            self.run_cli(tmpdir, "game", "pass", "--color", "white")
            finalized = json.loads(self.run_cli(tmpdir, "game", "finalize").stdout)
            self.assertEqual(finalized["result"]["status"], "finished")
            self.assertEqual(finalized["result"]["applied_event"]["kind"], "finalize")

            blocked_resume = json.loads(self.run_cli(tmpdir, "game", "resume", check=False).stdout)
            self.assertFalse(blocked_resume["ok"])

            rendered = Path(tmpdir, "game.txt").read_text(encoding="utf-8")
            self.assertIn("Status:       Finished", rendered)
            self.assertIn("Last event: Finalize game after scoring", rendered)

    def test_session_scoring_resume_finalize_is_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "session", "create", "--name", "center-read")
            self.run_cli(tmpdir, "session", "pass", "--name", "center-read", "--color", "black")
            self.run_cli(tmpdir, "session", "pass", "--name", "center-read", "--color", "white")

            resumed = json.loads(self.run_cli(tmpdir, "session", "resume", "--name", "center-read").stdout)
            self.assertEqual(resumed["result"]["status"], "active")
            self.assertEqual(resumed["result"]["applied_event"]["kind"], "resume")

            self.run_cli(tmpdir, "session", "pass", "--name", "center-read", "--color", "black")
            self.run_cli(tmpdir, "session", "pass", "--name", "center-read", "--color", "white")
            finalized = json.loads(self.run_cli(tmpdir, "session", "finalize", "--name", "center-read").stdout)
            self.assertEqual(finalized["result"]["status"], "finished")

            canonical = json.loads(self.run_cli(tmpdir, "game", "show").stdout)
            self.assertEqual(canonical["result"]["state"]["status"], "active")
            self.assertEqual(canonical["result"]["state"]["move_number"], 0)

    def test_cli_play_updates_rendered_board(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            initial_game = Path(tmpdir, "game.txt").read_text(encoding="utf-8")

            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")
            after_first_play = Path(tmpdir, "game.txt").read_text(encoding="utf-8")
            self.assertNotEqual(after_first_play, initial_game)
            self.assertIn("(X)", after_first_play)

            self.run_cli(tmpdir, "game", "play", "--color", "white", "--move", "D5")
            after_second_play = Path(tmpdir, "game.txt").read_text(encoding="utf-8")
            self.assertNotEqual(after_second_play, after_first_play)
            self.assertIn("(O)", after_second_play)

    def test_cli_parallel_play_and_render_leave_render_in_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")

            play_process = subprocess.Popen(
                ["python3", str(REPO_ROOT / "go_ref.py"), "game", "play", "--color", "black", "--move", "E5"],
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            render_process = subprocess.Popen(
                ["python3", str(REPO_ROOT / "go_ref.py"), "game", "render"],
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            play_stdout, play_stderr = play_process.communicate()
            render_stdout, render_stderr = render_process.communicate()

            self.assertEqual(play_process.returncode, 0, msg=play_stderr)
            self.assertEqual(render_process.returncode, 0, msg=render_stderr)
            self.assertTrue(json.loads(play_stdout)["ok"])
            self.assertTrue(json.loads(render_stdout)["ok"])

            shown = json.loads(self.run_cli(tmpdir, "game", "show").stdout)
            self.assertEqual(shown["result"]["state"]["move_number"], 1)

            rendered = Path(tmpdir, "game.txt").read_text(encoding="utf-8")
            self.assertIn("(X)", rendered)

    def test_cli_parallel_play_and_query_observe_a_consistent_game_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            lock_path = Path(tmpdir, ".state.json.lock")

            for _ in range(20):
                ticket_before = read_lock_queue_ticket(lock_path) if lock_path.exists() else 0
                play_process = subprocess.Popen(
                    ["python3", str(REPO_ROOT / "go_ref.py"), "game", "play", "--color", "black", "--move", "E5"],
                    cwd=tmpdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                wait_for_lock_queue(lock_path, minimum_next_ticket=ticket_before + 1)
                query_process = subprocess.Popen(
                    ["python3", str(REPO_ROOT / "go_ref.py"), "game", "query", "board"],
                    cwd=tmpdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                play_stdout, play_stderr = play_process.communicate()
                query_stdout, query_stderr = query_process.communicate()

                self.assertEqual(play_process.returncode, 0, msg=play_stderr)
                self.assertEqual(query_process.returncode, 0, msg=query_stderr)
                self.assertTrue(json.loads(play_stdout)["ok"])

                query_payload = json.loads(query_stdout)
                self.assertTrue(query_payload["ok"])
                self.assertEqual(query_payload["result"]["chain_summary"]["black_chain_count"], 1)
                self.assertEqual(query_payload["result"]["side_to_move"], "white")

                self.run_cli(tmpdir, "game", "undo")

    def test_game_init_clears_existing_sessions_and_reports_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")
            self.run_cli(tmpdir, "session", "create", "--name", "saved-read")
            temp_created = json.loads(self.run_cli(tmpdir, "session", "temp").stdout)
            temp_name = temp_created["result"]["session"]["name"]
            self.assertTrue(Path(tmpdir, "analysis/sessions", "saved-read").exists())
            self.assertTrue(Path(tmpdir, "analysis/sessions", temp_name).exists())

            init_payload = json.loads(self.run_cli(tmpdir, "game", "init").stdout)
            self.assertTrue(init_payload["ok"])
            self.assertEqual(init_payload["result"]["state"]["move_number"], 0)
            self.assertEqual(sorted(init_payload["result"]["sessions_cleared"]), sorted(["saved-read", temp_name]))

            listed = json.loads(self.run_cli(tmpdir, "session", "list").stdout)
            self.assertEqual(listed["result"]["sessions"], [])
            self.assertFalse(Path(tmpdir, "analysis/sessions", "saved-read").exists())
            self.assertFalse(Path(tmpdir, "analysis/sessions", temp_name).exists())

    def test_session_lifecycle_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")

            created = json.loads(self.run_cli(tmpdir, "session", "create", "--name", "semeai-1").stdout)
            self.assertTrue(created["ok"])
            self.assertEqual(created["result"]["session"]["name"], "semeai-1")
            self.assertEqual(created["result"]["session"]["kind"], "persistent")
            self.assertTrue(created["result"]["target"]["state_path"].endswith("analysis/sessions/semeai-1/state.json"))

            listed = json.loads(self.run_cli(tmpdir, "session", "list").stdout)
            self.assertTrue(listed["ok"])
            self.assertEqual([session["session"]["name"] for session in listed["result"]["sessions"]], ["semeai-1"])

            shown = json.loads(self.run_cli(tmpdir, "session", "show", "--name", "semeai-1").stdout)
            self.assertTrue(shown["ok"])
            self.assertEqual(shown["result"]["state"]["move_number"], 1)

            child = json.loads(self.run_cli(tmpdir, "session", "create", "--name", "ko-read", "--from", "session:semeai-1").stdout)
            self.assertTrue(child["ok"])
            self.assertEqual(child["result"]["session"]["base"]["ref"], "session:semeai-1")

            deleted = json.loads(self.run_cli(tmpdir, "session", "delete", "--name", "ko-read").stdout)
            self.assertTrue(deleted["ok"])
            self.assertEqual(deleted["result"]["session"]["name"], "ko-read")
            self.assertFalse(Path(tmpdir, "analysis/sessions/ko-read").exists())

    def test_session_analysis_is_isolated_from_canonical_game(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")
            self.run_cli(tmpdir, "session", "create", "--name", "center")

            canonical_state_before = Path(tmpdir, "state.json").read_text(encoding="utf-8")
            canonical_game_before = Path(tmpdir, "game.txt").read_text(encoding="utf-8")

            played = json.loads(self.run_cli(tmpdir, "session", "play", "--name", "center", "--color", "white", "--move", "D5").stdout)
            self.assertTrue(played["ok"])
            self.assertEqual(played["result"]["target"]["kind"], "session")

            session_show = json.loads(self.run_cli(tmpdir, "session", "show", "--name", "center").stdout)
            self.assertEqual(session_show["result"]["state"]["move_number"], 2)

            canonical_show = json.loads(self.run_cli(tmpdir, "game", "show").stdout)
            self.assertEqual(canonical_show["result"]["state"]["move_number"], 1)

            session_query = json.loads(self.run_cli(tmpdir, "session", "query", "--name", "center", "board").stdout)
            self.assertTrue(session_query["ok"])
            self.assertEqual(session_query["result"]["side_to_move"], "black")

            self.run_cli(tmpdir, "session", "play", "--name", "center", "--color", "black", "--move", "C3")
            after_reply = json.loads(self.run_cli(tmpdir, "session", "query", "--name", "center", "board").stdout)
            self.assertEqual(after_reply["result"]["capture_counts"]["black"], 0)

            self.assertEqual(Path(tmpdir, "state.json").read_text(encoding="utf-8"), canonical_state_before)
            self.assertEqual(Path(tmpdir, "game.txt").read_text(encoding="utf-8"), canonical_game_before)

    def test_session_reset_undo_and_persist_only_affect_target_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")
            self.run_cli(tmpdir, "session", "create", "--name", "a")
            self.run_cli(tmpdir, "session", "create", "--name", "b")
            self.run_cli(tmpdir, "session", "play", "--name", "a", "--color", "white", "--move", "D5")
            self.run_cli(tmpdir, "session", "play", "--name", "b", "--color", "white", "--move", "C3")

            self.run_cli(tmpdir, "session", "undo", "--name", "a")
            shown_a = json.loads(self.run_cli(tmpdir, "session", "show", "--name", "a").stdout)
            shown_b = json.loads(self.run_cli(tmpdir, "session", "show", "--name", "b").stdout)
            shown_canonical = json.loads(self.run_cli(tmpdir, "game", "show").stdout)
            self.assertEqual(shown_a["result"]["state"]["move_number"], 1)
            self.assertEqual(shown_b["result"]["state"]["move_number"], 2)
            self.assertEqual(shown_canonical["result"]["state"]["move_number"], 1)

            self.run_cli(tmpdir, "session", "reset", "--name", "b", "--from", "session:a")
            reset_b = json.loads(self.run_cli(tmpdir, "session", "show", "--name", "b").stdout)
            self.assertEqual(reset_b["result"]["state"]["move_number"], 1)

            self.run_cli(tmpdir, "session", "reset", "--name", "a", "--from", "game")
            reset_a = json.loads(self.run_cli(tmpdir, "session", "show", "--name", "a").stdout)
            self.assertEqual(reset_a["result"]["state"]["move_number"], 1)

            persisted = json.loads(self.run_cli(tmpdir, "session", "persist", "--name", "a", "--as", "saved-a").stdout)
            self.assertEqual(persisted["result"]["session"]["kind"], "persistent")
            self.assertEqual(persisted["result"]["session"]["name"], "saved-a")

    def test_temp_sessions_are_queryable_and_can_be_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")

            temp_created = json.loads(self.run_cli(tmpdir, "session", "temp").stdout)
            temp_name = temp_created["result"]["session"]["name"]
            self.assertEqual(temp_created["result"]["session"]["kind"], "ephemeral")

            self.run_cli(tmpdir, "session", "play", "--name", temp_name, "--color", "white", "--move", "D5")
            queried = json.loads(self.run_cli(tmpdir, "session", "query", "--name", temp_name, "board").stdout)
            self.assertEqual(queried["result"]["side_to_move"], "black")

            promoted = json.loads(self.run_cli(tmpdir, "session", "persist", "--name", temp_name, "--as", "saved-temp").stdout)
            self.assertEqual(promoted["result"]["session"]["name"], "saved-temp")

    def test_session_metadata_tracks_kind_base_and_update_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")

            created = json.loads(self.run_cli(tmpdir, "session", "create", "--name", "main-read").stdout)
            created_meta = created["result"]["session"]
            self.assertEqual(created_meta["kind"], "persistent")
            self.assertEqual(created_meta["base"]["ref"], "game")

            temp_created = json.loads(self.run_cli(tmpdir, "session", "temp").stdout)
            temp_name = temp_created["result"]["session"]["name"]
            self.assertEqual(temp_created["result"]["session"]["kind"], "ephemeral")

            self.run_cli(tmpdir, "session", "play", "--name", "main-read", "--color", "white", "--move", "D5")
            shown = json.loads(self.run_cli(tmpdir, "session", "show", "--name", "main-read").stdout)
            shown_meta = shown["result"]["session"]
            self.assertGreaterEqual(shown_meta["updated_at"], shown_meta["created_at"])

            reset = json.loads(self.run_cli(tmpdir, "session", "reset", "--name", "main-read", "--from", f"session:{temp_name}").stdout)
            self.assertEqual(reset["result"]["session"]["base"]["ref"], f"session:{temp_name}")

            persisted = json.loads(self.run_cli(tmpdir, "session", "persist", "--name", temp_name, "--as", "saved-temp").stdout)
            self.assertEqual(persisted["result"]["session"]["kind"], "persistent")
            self.assertEqual(persisted["result"]["session"]["base"]["ref"], "game")

    def test_session_invalid_and_missing_cases_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")

            invalid = self.run_cli(tmpdir, "session", "create", "--name", "Bad Name", check=False)
            self.assertEqual(invalid.returncode, 1)
            self.assertFalse(json.loads(invalid.stdout)["ok"])

            self.run_cli(tmpdir, "session", "create", "--name", "readout")
            duplicate = self.run_cli(tmpdir, "session", "create", "--name", "readout", check=False)
            self.assertEqual(duplicate.returncode, 1)
            self.assertFalse(json.loads(duplicate.stdout)["ok"])

            missing_show = self.run_cli(tmpdir, "session", "show", "--name", "missing", check=False)
            self.assertEqual(missing_show.returncode, 1)
            self.assertFalse(json.loads(missing_show.stdout)["ok"])

            missing_delete = self.run_cli(tmpdir, "session", "delete", "--name", "missing", check=False)
            self.assertEqual(missing_delete.returncode, 1)
            self.assertFalse(json.loads(missing_delete.stdout)["ok"])

            invalid_source = self.run_cli(tmpdir, "session", "create", "--name", "bad-source", "--from", "branch:abc", check=False)
            self.assertEqual(invalid_source.returncode, 1)
            self.assertFalse(json.loads(invalid_source.stdout)["ok"])

    def test_temp_session_player_flow_preserves_canonical_until_final_move(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "E5")
            self.run_cli(tmpdir, "game", "play", "--color", "white", "--move", "D5")
            canonical_before = json.loads(self.run_cli(tmpdir, "game", "show").stdout)

            temp_created = json.loads(self.run_cli(tmpdir, "session", "temp").stdout)
            temp_name = temp_created["result"]["session"]["name"]

            self.run_cli(tmpdir, "session", "play", "--name", temp_name, "--color", "black", "--move", "C3")
            session_board = json.loads(self.run_cli(tmpdir, "session", "query", "--name", temp_name, "board").stdout)
            self.assertEqual(session_board["result"]["side_to_move"], "white")

            self.run_cli(tmpdir, "session", "persist", "--name", temp_name, "--as", "candidate-c3")
            canonical_mid = json.loads(self.run_cli(tmpdir, "game", "show").stdout)
            self.assertEqual(canonical_before["result"]["state"]["move_number"], canonical_mid["result"]["state"]["move_number"])

            self.run_cli(tmpdir, "game", "play", "--color", "black", "--move", "C3")
            canonical_after = json.loads(self.run_cli(tmpdir, "game", "show").stdout)
            self.assertEqual(canonical_after["result"]["state"]["move_number"], canonical_before["result"]["state"]["move_number"] + 1)

    def test_same_session_parallel_play_and_render_leave_session_render_in_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "session", "create", "--name", "race")

            play_process = subprocess.Popen(
                ["python3", str(REPO_ROOT / "go_ref.py"), "session", "play", "--name", "race", "--color", "black", "--move", "E5"],
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            render_process = subprocess.Popen(
                ["python3", str(REPO_ROOT / "go_ref.py"), "session", "render", "--name", "race"],
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            play_stdout, play_stderr = play_process.communicate()
            render_stdout, render_stderr = render_process.communicate()

            self.assertEqual(play_process.returncode, 0, msg=play_stderr)
            self.assertEqual(render_process.returncode, 0, msg=render_stderr)
            self.assertTrue(json.loads(play_stdout)["ok"])
            self.assertTrue(json.loads(render_stdout)["ok"])

            shown = json.loads(self.run_cli(tmpdir, "session", "show", "--name", "race").stdout)
            self.assertEqual(shown["result"]["state"]["move_number"], 1)

            rendered = Path(tmpdir, "analysis/sessions/race/game.txt").read_text(encoding="utf-8")
            self.assertIn("(X)", rendered)

    def test_same_session_parallel_play_and_query_leave_session_state_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run_cli(tmpdir, "game", "init")
            self.run_cli(tmpdir, "session", "create", "--name", "race")

            for _ in range(20):
                play_process = subprocess.Popen(
                    ["python3", str(REPO_ROOT / "go_ref.py"), "session", "play", "--name", "race", "--color", "black", "--move", "E5"],
                    cwd=tmpdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                query_process = subprocess.Popen(
                    ["python3", str(REPO_ROOT / "go_ref.py"), "session", "query", "--name", "race", "board"],
                    cwd=tmpdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                play_stdout, play_stderr = play_process.communicate()
                query_stdout, query_stderr = query_process.communicate()

                self.assertEqual(play_process.returncode, 0, msg=play_stderr)
                self.assertEqual(query_process.returncode, 0, msg=query_stderr)
                self.assertTrue(json.loads(play_stdout)["ok"])

                query_payload = json.loads(query_stdout)
                self.assertTrue(query_payload["ok"])

                shown = json.loads(self.run_cli(tmpdir, "session", "show", "--name", "race").stdout)
                self.assertEqual(shown["result"]["state"]["move_number"], 1)

                self.run_cli(tmpdir, "session", "undo", "--name", "race")


class PlayerDocsTests(unittest.TestCase):
    def test_gameplay_governance_requires_strongest_reply_check_for_sharp_candidates(self) -> None:
        text = (REPO_ROOT / "docs" / "agents" / "player" / "gameplay-governance.md").read_text(encoding="utf-8")
        self.assertIn("After that, let the position determine the reading.", text)
        self.assertIn("This is not a move-selection algorithm.", text)
        self.assertIn("## Post-Move Factual Audit", text)
        self.assertIn("Do not assume", text)
        self.assertIn("connection equals safety", text)
        self.assertIn("## Role-Based Candidate Discipline", text)
        self.assertIn("urgent defense or capture", text)
        self.assertIn("move elsewhere that takes profit or initiative", text)
        self.assertIn("Before trusting a sharp local move, read White's strongest obvious local reply", text)
        self.assertIn("A move is not validated by finding one friendly continuation.", text)
        self.assertIn("If Black's move only relocates liberties", text)
        self.assertIn("Do not confuse short-term severity with profit.", text)
        self.assertIn("Continue until the local fight is actually", text)
        self.assertIn("stable, or until the candidate is clearly worse", text)
        self.assertIn("## Global Reset After Material Change", text)
        self.assertIn("what changed on the full board", text)
        self.assertIn("## Concrete Language Discipline", text)
        self.assertIn("reasoning falsifiable", text)
        self.assertIn("## Tooling Appendix", text)
        self.assertIn("### Essential Bookkeeping", text)
        self.assertIn("### Useful But Optional", text)
        self.assertIn("### Too Opinionated", text)

    def test_session_prompt_warns_against_one_ply_sharp_moves(self) -> None:
        text = (REPO_ROOT / "docs" / "agents" / "player" / "session-prompt.md").read_text(encoding="utf-8")
        self.assertIn("query the resulting", text)
        self.assertIn("weak Black chain", text)
        self.assertIn("Do not trust one-ply severity by itself.", text)
        self.assertIn("Read White's strongest obvious", text)
        self.assertIn("better", text)
        self.assertIn("shape or cleaner result", text)
        self.assertIn("safe, thick, or calm", text)
        self.assertIn("briefly reset", text)
        self.assertIn("whole board", text)

    def test_coder_guidance_prefers_principles_over_ritual_for_player_docs(self) -> None:
        text = (REPO_ROOT / "docs" / "agents" / "coder" / "project-guidance.md").read_text(encoding="utf-8")
        self.assertIn("optimize for better", text)
        self.assertIn("judgment, not more ritual", text)
        self.assertIn("Prefer principle-based wording over over-prescriptive procedures.", text)
        self.assertIn("If a docs change would make Codex more compliant but less thoughtful", text)
        self.assertIn("This repo exists to study GPT/Codex's ability to reason about Go", text)
        self.assertIn("Treat the tools as:", text)
        self.assertIn("Codex's eyes into the position", text)
        self.assertIn("Do not turn the tools into:", text)
        self.assertIn("a move recommender", text)


if __name__ == "__main__":
    unittest.main()
