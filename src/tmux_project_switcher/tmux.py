"""The only module that talks to the tmux binary.

tmux-project-switcher records metadata with tmux user options instead of a side file:
  @tmux_project_switcher_path         on a session: the project directory it was opened for
  @tmux_project_switcher_window_slot  on a window: the window slot it runs
  @tmux_project_switcher_pane_slot    on a pane: the pane slot it runs

Window and pane tags are separate because tmux shows window options in pane
formats, which would make a window tag look like a pane tag.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

TAG_PATH = "@tmux_project_switcher_path"
TAG_WINDOW_SLOT = "@tmux_project_switcher_window_slot"
TAG_PANE_SLOT = "@tmux_project_switcher_pane_slot"


class TmuxError(RuntimeError):
    pass


@dataclass(frozen=True)
class Session:
    name: str
    path: str  # "" if the session was not opened by tmux-project-switcher


def _call(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def _must(*args: str) -> str:
    proc = _call(*args)
    if proc.returncode != 0:
        raise TmuxError(proc.stderr.strip() or f"tmux {args[0]} failed")
    return proc.stdout


def inside_tmux() -> bool:
    return bool(os.environ.get("TMUX"))


def current_session() -> str:
    return _must("display-message", "-p", "#{session_name}").strip()


def list_sessions() -> list[Session]:
    proc = _call("list-sessions", "-F", f"#{{session_name}}\t#{{{TAG_PATH}}}")
    if proc.returncode != 0:  # no server running
        return []
    sessions = []
    for line in proc.stdout.splitlines():
        name, _, path = line.partition("\t")
        if name:
            sessions.append(Session(name, path))
    return sessions


def create_session(name: str, path: str) -> None:
    _must("new-session", "-d", "-s", name, "-c", path)
    _must("set-option", "-q", "-t", name, TAG_PATH, path)


def switch(name: str) -> None:
    _must("switch-client", "-t", f"={name}")


def attach(name: str) -> None:
    # Replaces the current process: attach needs the real terminal, so no pipes here.
    os.execvp("tmux", ["tmux", "attach-session", "-t", f"={name}"])


def _find_tagged(args: list[str], id_fmt: str, tag: str, slot: str) -> str | None:
    out = _must(*args, "-F", f"{id_fmt}\t#{{{tag}}}")
    for line in out.splitlines():
        item_id, _, value = line.partition("\t")
        if value == slot:
            return item_id
    return None


def ensure_window(session: str, slot: str, command: str, cwd: str) -> None:
    window = _find_tagged(
        ["list-windows", "-t", f"={session}"], "#{window_id}", TAG_WINDOW_SLOT, slot
    )
    if window is None:
        window = _must(
            "new-window", "-d", "-P", "-F", "#{window_id}",
            "-t", f"{session}:", "-c", cwd, command,
        ).strip()
        _must("set-option", "-w", "-q", "-t", window, TAG_WINDOW_SLOT, slot)
    _must("select-window", "-t", window)


def ensure_pane(session: str, slot: str, command: str, cwd: str, split: str) -> None:
    pane = _find_tagged(
        ["list-panes", "-s", "-t", f"={session}"], "#{pane_id}", TAG_PANE_SLOT, slot
    )
    if pane is None:
        flag = "-h" if split == "right" else "-v"
        pane = _must(
            "split-window", flag, "-d", "-P", "-F", "#{pane_id}",
            "-t", f"{session}:", "-c", cwd, command,
        ).strip()
        _must("set-option", "-p", "-q", "-t", pane, TAG_PANE_SLOT, slot)
    _must("select-pane", "-t", pane)
