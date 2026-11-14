import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tmux_project_switcher.config import ConfigError, Root, config_path, load, parse


class ParseTests(unittest.TestCase):
    def test_parse_without_roots_adds_no_defaults(self):
        cfg = parse({})
        self.assertEqual(cfg.roots, [])
        self.assertEqual(cfg.slots, {})

    def test_string_and_table_roots(self):
        cfg = parse({"roots": ["/tmp/a", {"path": "/tmp/b", "depth": 3}]})
        self.assertEqual(cfg.roots, [Root(Path("/tmp/a"), 1), Root(Path("/tmp/b"), 3)])

    def test_root_paths_expand_environment_variables(self):
        with mock.patch.dict(os.environ, {"PROJECTS_HOME": "/srv/code"}):
            cfg = parse({"roots": ["$PROJECTS_HOME/app", {"path": "${PROJECTS_HOME}/x", "depth": 2}]})
        self.assertEqual(cfg.roots, [Root(Path("/srv/code/app"), 1), Root(Path("/srv/code/x"), 2)])


class LocationTests(unittest.TestCase):
    def test_default_location_is_under_xdg_config_home(self):
        env = {"XDG_CONFIG_HOME": "/xdg", "TMUX_PROJECT_SWITCHER_CONFIG": ""}
        with mock.patch.dict(os.environ, env):
            self.assertEqual(config_path(), Path("/xdg/tmux-project-switcher/config.toml"))

    def test_explicit_env_var_overrides_location(self):
        with mock.patch.dict(os.environ, {"TMUX_PROJECT_SWITCHER_CONFIG": "/etc/my.toml"}):
            self.assertEqual(config_path(), Path("/etc/my.toml"))

    def test_load_reads_roots_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_file = Path(tmp) / "config.toml"
            cfg_file.write_text('roots = ["/work/one", { path = "/work/two", depth = 2 }]\n')
            cfg = load(cfg_file)
        self.assertEqual(cfg.roots, [Root(Path("/work/one"), 1), Root(Path("/work/two"), 2)])

    def test_missing_file_uses_default_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load(Path(tmp) / "absent.toml")
        self.assertTrue(cfg.roots)
        self.assertEqual(cfg.roots[0].path.name, "projects")

    def test_existing_file_without_roots_ignores_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_file = Path(tmp) / "config.toml"
            cfg_file.write_text('[slot.logs]\ncommand = "tail -f /dev/null"\n')
            cfg = load(cfg_file)
        self.assertEqual(cfg.roots, [])
        self.assertIn("logs", cfg.slots)

    def test_load_reports_malformed_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_file = Path(tmp) / "config.toml"
            cfg_file.write_text("roots = [\n")
            with self.assertRaises(ConfigError):
                load(cfg_file)

    def test_depth_must_be_positive_integer(self):
        for depth in (0, -1, "2", True):
            with self.subTest(depth=depth), self.assertRaises(ConfigError):
                parse({"roots": [{"path": "/tmp", "depth": depth}]})

    def test_slot_defaults(self):
        slot = parse({"slot": {"logs": {"command": "tail -f x"}}}).slots["logs"]
        self.assertEqual((slot.placement, slot.split), ("window", "right"))

    def test_invalid_slots_are_rejected(self):
        bad_configs = [
            {"slot": {"bad name": {"command": "x"}}},
            {"slot": {"a": {"command": "  "}}},
            {"slot": {"a": {"command": "x", "placement": "tab"}}},
            {"slot": {"a": {"command": "x", "split": "diagonal"}}},
        ]
        for bad in bad_configs:
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                parse(bad)


if __name__ == "__main__":
    unittest.main()
