import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from maze_solver import (
    compare_maze_files,
    discover_maze_files,
    load_maze,
    parse_maze_text,
    solve_maze,
)


class MazeSolverTests(unittest.TestCase):
    def test_solves_shortest_path(self):
        maze = parse_maze_text("#####\n#A  #\n### #\n#B  #\n#####\n")
        path = solve_maze(maze)

        self.assertEqual(path[0], maze.start)
        self.assertEqual(path[-1], maze.goal)
        self.assertEqual(len(path) - 1, 6)
        self.assertTrue(all(maze.is_walkable(position) for position in path))

    def test_accepts_alternate_markers_and_ragged_rows(self):
        maze = parse_maze_text("S..\n##E")

        self.assertEqual(maze.width, 3)
        self.assertEqual(solve_maze(maze), [(0, 0), (0, 1), (0, 2), (1, 2)])

    def test_rejects_missing_or_duplicate_markers(self):
        for text in ("###\n#A#\n###", "A.B\nA.."):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_maze_text(text)

    def test_reports_unreachable_goal(self):
        maze = parse_maze_text("#####\n#A#B#\n#####")

        with self.assertRaisesRegex(ValueError, "nav iespējams"):
            solve_maze(maze)

    def test_discovers_and_solves_existing_maps(self):
        maze_files = discover_maze_files(Path(__file__).parent)

        self.assertGreaterEqual(len(maze_files), 4)
        for maze_file in maze_files:
            with self.subTest(maze=maze_file.name):
                maze = load_maze(maze_file)
                path = solve_maze(maze)
                self.assertEqual(path[0], maze.start)
                self.assertEqual(path[-1], maze.goal)

    def test_comparison_reports_steps_and_search_time(self):
        maze_files = discover_maze_files(Path(__file__).parent)

        comparisons = compare_maze_files(maze_files)

        self.assertEqual(len(comparisons), len(maze_files))
        for comparison in comparisons:
            with self.subTest(maze=comparison.path.name):
                self.assertIsNone(comparison.error)
                self.assertIsNotNone(comparison.steps)
                self.assertGreaterEqual(comparison.steps, 0)
                self.assertIsNotNone(comparison.elapsed_ms)
                self.assertGreaterEqual(comparison.elapsed_ms, 0)

    def test_discovers_a_new_maze_in_a_subfolder(self):
        with TemporaryDirectory() as temporary_directory:
            maze_path = Path(temporary_directory) / "new_maps" / "classmate.txt"
            maze_path.parent.mkdir()
            maze_path.write_text("#####\n#A B#\n#####\n", encoding="utf-8")
            ignored_path = (
                Path(temporary_directory) / ".venv" / "packages" / "ignored.txt"
            )
            ignored_path.parent.mkdir(parents=True)
            ignored_path.write_text("#####\n#A B#\n#####\n", encoding="utf-8")

            self.assertEqual(discover_maze_files(Path(temporary_directory)), [maze_path])


if __name__ == "__main__":
    unittest.main()
