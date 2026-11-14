"""Configuration for tmux-project-switcher.

The config file is TOML, read from $TMUX_PROJECT_SWITCHER_CONFIG or
$XDG_CONFIG_HOME/tmux-project-switcher/config.toml. It is parsed as data and never executed.
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

SLOT_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
PLACEMENTS = ("window", "pane")
SPLITS = ("right", "below")
DEFAULT_ROOTS = (Path.home() / "projects",)


class ConfigError(ValueError):
    """The config file is malformed."""


@dataclass(frozen=True)
class Root:
    """A directory whose children are projects, searched down to `depth` levels."""

    path: Path
    depth: int = 1


@dataclass(frozen=True)
class Slot:
    """A named command that is started once per session and then re-focused on demand."""

    name: str
    command: str
    placement: str = "window"  # "window" = its own window, "pane" = a split pane
    split: str = "right"  # for panes: "right" or "below"


@dataclass
class Config:
    roots: list[Root] = field(default_factory=list)
    slots: dict[str, Slot] = field(default_factory=dict)


def config_path() -> Path:
    explicit = os.environ.get("TMUX_PROJECT_SWITCHER_CONFIG")
    if explicit:
        return Path(explicit).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "tmux-project-switcher" / "config.toml"


def load(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        # No config file at all: fall back to the built-in default roots.
        return Config(roots=[Root(p) for p in DEFAULT_ROOTS])
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    return parse(data)


def parse(data: dict) -> Config:
    roots = _parse_roots(data.get("roots", []))
    slots = _parse_slots(data.get("slot", {}))
    # Once a config file exists, it is the only source of roots. No defaults are added here.
    return Config(roots=roots, slots=slots)


def _expand(text: str) -> Path:
    """Expand $VARS and a leading ~ so one config can be shared across machines."""
    return Path(os.path.expandvars(text)).expanduser()


def _parse_roots(items: object) -> list[Root]:
    if not isinstance(items, list):
        raise ConfigError("'roots' must be an array")
    roots: list[Root] = []
    for item in items:
        if isinstance(item, str):
            roots.append(Root(_expand(item)))
        elif isinstance(item, dict) and isinstance(item.get("path"), str):
            depth = item.get("depth", 1)
            if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
                raise ConfigError(f"root depth must be a positive integer: {item!r}")
            roots.append(Root(_expand(item["path"]), depth))
        else:
            raise ConfigError(f"invalid root entry: {item!r}")
    return roots


def _parse_slots(table: object) -> dict[str, Slot]:
    if not isinstance(table, dict):
        raise ConfigError("'slot' must be a table of named slots")
    slots: dict[str, Slot] = {}
    for name, spec in table.items():
        if not SLOT_NAME.match(name):
            raise ConfigError(f"invalid slot name {name!r}: use letters, digits, '-' or '_'")
        if not isinstance(spec, dict):
            raise ConfigError(f"slot {name!r} must be a table")
        command = spec.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ConfigError(f"slot {name!r}: 'command' must be a non-empty string")
        placement = spec.get("placement", "window")
        if placement not in PLACEMENTS:
            raise ConfigError(f"slot {name!r}: placement must be one of {PLACEMENTS}")
        split = spec.get("split", "right")
        if split not in SPLITS:
            raise ConfigError(f"slot {name!r}: split must be one of {SPLITS}")
        slots[name] = Slot(name, command, placement, split)
    return slots
