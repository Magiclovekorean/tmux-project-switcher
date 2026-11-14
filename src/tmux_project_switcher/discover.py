"""Find project directories and turn them into tmux session names."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from .config import Root

_TMUX_UNSAFE = re.compile(r"[.:\s]+")


def base_session_name(path: Path) -> str:
    """Session name derived from a directory name; tmux dislikes '.' and ':' in names."""
    name = _TMUX_UNSAFE.sub("_", path.name).strip("_")
    return name or "project"


def unique_session_name(path: Path, taken: dict[str, str]) -> str:
    """Pick a session name for `path`.

    `taken` maps existing session names to the project path they were opened
    for ("" when the session was not created by tmux-project-switcher). A name is free if it
    is unused or already belongs to this same path.
    """
    base = base_session_name(path)
    candidate, n = base, 2
    while candidate in taken and taken[candidate] != str(path):
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def find_projects(roots: list[Root]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.path.is_dir():
            continue
        for project in _walk(root.path, root.depth):
            if project not in seen:
                seen.add(project)
                found.append(project)
    return found


def _walk(base: Path, depth: int) -> Iterator[Path]:
    """Yield directories up to `depth` levels below `base`, breadth first.

    Hidden directories and symlinks are skipped. A directory that contains a
    `.git` entry is a project in its own right, so it is listed but not searched.
    """
    frontier = [base]
    for _ in range(depth):
        next_frontier: list[Path] = []
        for directory in frontier:
            try:
                children = sorted(directory.iterdir())
            except OSError:
                continue
            for child in children:
                if child.name.startswith(".") or child.is_symlink() or not child.is_dir():
                    continue
                yield child
                if not (child / ".git").exists():
                    next_frontier.append(child)
        frontier = next_frontier
