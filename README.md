# tmux-project-switcher

Jump between project directories and tmux sessions from one fuzzy finder.

- `tmux-project-switcher` opens an fzf list of running sessions and project directories. Picking a
  directory creates a session for it (or reuses the one already open) and attaches or switches.
- `tmux-project-switcher open PATH` does the same for a given directory.
- `tmux-project-switcher slots` lists configured slots. `tmux-project-switcher run SLOT` starts a slot's command in
  the current session the first time and focuses it afterwards.

## Requirements

- Python 3.11+ (standard library only)
- tmux 3.0+ (uses user options such as `@tmux_project_switcher_path`)
- fzf

## Install

```sh
pip install .
```

## Configuration

`$TMUX_PROJECT_SWITCHER_CONFIG`, or `$XDG_CONFIG_HOME/tmux-project-switcher/config.toml` (default `~/.config/tmux-project-switcher/config.toml`):

```toml
# Directories whose children are projects. Plain strings mean depth 1.
roots = ["~/code", { path = "~/work", depth = 2 }]

# A slot is a command started once per session and re-focused later.
[slot.logs]
command = "tail -f /var/log/app.log"
placement = "window"        # "window" (default) or "pane"

[slot.repl]
command = "python3"
placement = "pane"
split = "below"             # "right" (default) or "below"
```

Without a config file, `~/projects` is searched at depth 1. Once a config file exists, only the
`roots` it lists are searched. No default roots are added, so a config without `roots` finds no projects.

Discovery rules: hidden directories and symlinks are skipped. A directory containing `.git`
is listed as a project and not searched further.

## Design notes

- Config is TOML, parsed as data. Nothing is sourced or executed from the config
  or from the current directory.
- Session and pane identity is stored in tmux user options, so there is no cache file to
  clean up. A dead pane simply stops matching.
- Session names come from directory names with `.`, `:` and whitespace replaced by `_`.
  Two projects with the same name get `-2`, `-3`, ... suffixes.

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

## License

MIT. See [LICENSE](LICENSE).
