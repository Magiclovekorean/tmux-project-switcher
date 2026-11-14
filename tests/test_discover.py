import tempfile
import unittest
from pathlib import Path

from tmux_project_switcher.config import Root
from tmux_project_switcher.discover import base_session_name, find_projects, unique_session_name


class NamingTests(unittest.TestCase):
    def test_dots_colons_and_spaces_become_underscores(self):
        self.assertEqual(base_session_name(Path("/x/my.app:v2")), "my_app_v2")
        self.assertEqual(base_session_name(Path("/x/hello world")), "hello_world")

    def test_same_path_reuses_its_name(self):
        self.assertEqual(unique_session_name(Path("/a/app"), {"app": "/a/app"}), "app")

    def test_collisions_get_numeric_suffixes(self):
        taken = {"app": "/a/app", "app-2": "/b/app"}
        self.assertEqual(unique_session_name(Path("/c/app"), taken), "app-3")

    def test_untagged_session_is_never_reused(self):
        self.assertEqual(unique_session_name(Path("/a/app"), {"app": ""}), "app-2")


class FindProjectsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def mkdirs(self, *parts):
        self.root.joinpath(*parts).mkdir(parents=True)

    def rel(self, projects):
        return [p.relative_to(self.root).as_posix() for p in projects]

    def test_depth_one_lists_children_only(self):
        self.mkdirs("a")
        self.mkdirs("b", "c")
        self.assertEqual(self.rel(find_projects([Root(self.root, 1)])), ["a", "b"])

    def test_depth_two_is_breadth_first(self):
        self.mkdirs("a", "x")
        self.mkdirs("b")
        self.assertEqual(self.rel(find_projects([Root(self.root, 2)])), ["a", "b", "a/x"])

    def test_git_repo_is_listed_but_not_searched(self):
        self.mkdirs("repo")
        self.mkdirs("repo", ".git")
        self.mkdirs("repo", "nested")
        self.assertEqual(self.rel(find_projects([Root(self.root, 2)])), ["repo"])

    def test_hidden_directories_and_missing_roots_are_skipped(self):
        self.mkdirs(".hidden")
        found = find_projects([Root(self.root / "missing", 1), Root(self.root, 1)])
        self.assertEqual(found, [])

    def test_overlapping_roots_do_not_duplicate(self):
        self.mkdirs("a")
        self.assertEqual(len(find_projects([Root(self.root, 1), Root(self.root, 1)])), 1)


if __name__ == "__main__":
    unittest.main()
