import tempfile
import unittest
from pathlib import Path

from Ance_maze import (
    breadth_first_search,
    discover_mazes,
    depth_first_search,
    load_maze,
)


class MazeSolverTests(unittest.TestCase):
    def load_text(self, text: str):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        path = Path(temporary_directory.name) / "maze.txt"
        path.write_text(text, encoding="utf-8")
        return load_maze(path)

    def test_breadth_first_search_finds_shortest_path(self):
        maze = self.load_text("#######\n#A#   #\n# # #B#\n#     #\n#######\n")

        result = breadth_first_search(maze)

        self.assertEqual(result.steps, 7)
        self.assertEqual(result.path[0], maze.start)
        self.assertEqual(result.path[-1], maze.goal)
        for (x1, y1), (x2, y2) in zip(result.path, result.path[1:]):
            self.assertEqual(abs(x1 - x2) + abs(y1 - y2), 1)
            self.assertNotEqual(maze.rows[y2][x2], "#")

    def test_depth_first_search_finds_a_valid_path(self):
        maze = self.load_text("#######\n#A#   #\n# # #B#\n#     #\n#######\n")

        result = depth_first_search(maze)

        self.assertIsNotNone(result.path)
        self.assertEqual(result.path[0], maze.start)
        self.assertEqual(result.path[-1], maze.goal)

    def test_search_reports_when_goal_is_unreachable(self):
        maze = self.load_text("#####\n#A#B#\n#####\n")

        self.assertIsNone(breadth_first_search(maze).path)
        self.assertIsNone(depth_first_search(maze).path)

    def test_loader_rejects_missing_or_duplicate_markers(self):
        with self.assertRaisesRegex(ValueError, "tieši viens"):
            self.load_text("######\n#AA B#\n######\n")

    def test_loader_rejects_non_rectangular_maps(self):
        with self.assertRaisesRegex(ValueError, "vienādā platumā"):
            self.load_text("#####\n#A B#\n####\n")

    def test_map_name_comes_from_filename(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "Ances labirints.txt"
            path.write_text("#####\n#A B#\n#####\n", encoding="utf-8")

            maze = load_maze(path)

        self.assertEqual(maze.name, "Ances labirints")

    def test_map_discovery_skips_requirements_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            (folder / "requirements.txt").write_text("pygame-ce>=2.5.3\n", encoding="utf-8")
            (folder / "sample.txt").write_text("#####\n#A B#\n#####\n", encoding="utf-8")

            files, errors = discover_mazes(folder)

        self.assertEqual([path.name for path in files], ["sample.txt"])
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
