"""Command line interface: pick, open, run, slots."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, tmux
from .config import Config, ConfigError, load
from .discover import find_projects, unique_session_name


class UsageError(RuntimeError):
    pass


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ConfigError, tmux.TmuxError, UsageError) as exc:
        print(f"tmux-project-switcher: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tmux-project-switcher",
        description="Jump between project directories and tmux sessions.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.set_defaults(handler=cmd_pick)

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("pick", help="choose a session or project with fzf (default)").set_defaults(
        handler=cmd_pick
    )

    p_open = sub.add_parser("open", help="open a directory as a session")
    p_open.add_argument("path")
    p_open.set_defaults(handler=cmd_open)

    p_run = sub.add_parser("run", help="start or focus a slot in the current session")
    p_run.add_argument("slot")
    p_run.set_defaults(handler=cmd_run)

    sub.add_parser("slots", help="list configured slots").set_defaults(handler=cmd_slots)
    return parser


def cmd_pick(_args: argparse.Namespace) -> int:
    if shutil.which("fzf") is None:
        raise UsageError("fzf is not installed")

    cfg = load()
    sessions = tmux.list_sessions()
    current = tmux.current_session() if tmux.inside_tmux() else None

    choices: dict[str, tuple[str, str]] = {}
    for s in sessions:
        if s.name != current:
            choices[f"session  {s.name}"] = ("session", s.name)

    open_paths = {s.path for s in sessions if s.path}
    for project in find_projects(cfg.roots):
        if str(project) not in open_paths:
            choices[f"project  {_tilde(project)}"] = ("dir", str(project))

    if not choices:
        if not cfg.roots:
            raise UsageError("nothing to pick: the config file has no 'roots' entries")
        raise UsageError("nothing to pick: no sessions and no projects in the configured roots")

    proc = subprocess.run(
        ["fzf", "--prompt=project> ", "--reverse", "--height=40%"],
        input="\n".join(choices),
        stdout=subprocess.PIPE,
        text=True,
    )
    selected = proc.stdout.strip()
    if proc.returncode != 0 or not selected:
        return 0

    kind, value = choices[selected]
    if kind == "session":
        return _switch(value)
    return open_project(Path(value))


def cmd_open(args: argparse.Namespace) -> int:
    return open_project(Path(args.path))


def cmd_run(args: argparse.Namespace) -> int:
    cfg: Config = load()
    slot = cfg.slots.get(args.slot)
    if slot is None:
        raise UsageError(f"no slot named {args.slot!r}; see `tmux-project-switcher slots`")
    if not tmux.inside_tmux():
        raise UsageError("`run` must be used inside a tmux session")

    session = tmux.current_session()
    project_paths = {s.name: s.path for s in tmux.list_sessions()}
    cwd = project_paths.get(session) or os.getcwd()

    if slot.placement == "window":
        tmux.ensure_window(session, slot.name, slot.command, cwd)
    else:
        tmux.ensure_pane(session, slot.name, slot.command, cwd, slot.split)
    return 0


def cmd_slots(_args: argparse.Namespace) -> int:
    cfg = load()
    if not cfg.slots:
        print("no slots configured")
        return 0
    for slot in cfg.slots.values():
        print(f"{slot.name:<16} {slot.placement:<7} {slot.command}")
    return 0


def open_project(path: Path) -> int:
    path = path.expanduser().resolve()
    if not path.is_dir():
        raise UsageError(f"not a directory: {path}")

    sessions = tmux.list_sessions()
    for s in sessions:
        if s.path == str(path):
            return _switch(s.name)

    name = unique_session_name(path, {s.name: s.path for s in sessions})
    tmux.create_session(name, str(path))
    return _switch(name)


def _switch(name: str) -> int:
    if tmux.inside_tmux():
        tmux.switch(name)
        return 0
    tmux.attach(name)  # does not return
    return 0


def _tilde(path: Path) -> str:
    home = str(Path.home())
    text = str(path)
    if text.startswith(home + os.sep):
        return "~" + text[len(home):]
    return text
