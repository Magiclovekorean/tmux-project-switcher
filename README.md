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

### With Nix (flakes)

The flake builds the package, runs the unit tests, and wraps the binary so `tmux` and `fzf`
are on its `PATH` (after your own, so it uses the same tmux as your running server).

Flakes only see files tracked by git, so when installing from a local checkout, run
`git add -A` first. Committing is not required.

Try it without installing:

```sh
nix run github:Magiclovekorean/tmux-project-switcher -- slots
# or, from a local checkout:
nix run . -- slots
```

Install into your user profile:

```sh
nix profile install github:Magiclovekorean/tmux-project-switcher
# or, from a local checkout:
nix profile install .
```

#### With Home Manager (NixOS or standalone)

Add the flake as an input of your configuration flake:

```nix
# flake.nix
inputs.tmux-project-switcher.url = "github:Magiclovekorean/tmux-project-switcher";
# for development, a local checkout works too:
# inputs.tmux-project-switcher.url = "path:/home/<you>/path/to/tmux-project-switcher";
```

Pass `inputs` to your Home Manager modules (`extraSpecialArgs = { inherit inputs; };`
for standalone Home Manager, or `home-manager.extraSpecialArgs` in NixOS), then in a module:

```nix
{ inputs, pkgs, ... }:
{
  home.packages = [
    inputs.tmux-project-switcher.packages.${pkgs.system}.default
  ];

  # Optional: manage the config file from Nix.
  xdg.configFile."tmux-project-switcher/config.toml".text = ''
    roots = ["$HOME/code", { path = "$HOME/work", depth = 2 }]

    [slot.logs]
    command = "tail -f /var/log/app.log"
  '';
}
```

After changing the input, update the lock file and switch:

```sh
nix flake update tmux-project-switcher
home-manager switch    # or: sudo nixos-rebuild switch
```

### With pip

```sh
pip install .
```

## Configuration

The config file is read from the first of these that applies:

1. `$TMUX_PROJECT_SWITCHER_CONFIG`, if set (`~` is expanded).
2. `$XDG_CONFIG_HOME/tmux-project-switcher/config.toml`, if `XDG_CONFIG_HOME` is set.
3. `~/.config/tmux-project-switcher/config.toml`.

A complete example:

```toml
# Project roots: directories whose children are projects.
roots = [
  "~/code",                          # depth 1: ~/code/<project>
  { path = "~/work", depth = 2 },    # depth 2: ~/work/<group>/<project>
]

# Slots: commands started once per session and re-focused on later runs.
[slot.logs]
command = "tail -f /var/log/app.log"  # required, non-empty string
placement = "window"                  # "window" (default) or "pane"

[slot.server]
command = "npm run dev"
placement = "pane"
split = "right"                       # "right" (default) or "below"; only used for panes
```

### `roots`

Must be an array. Each entry is either a string (depth 1) or a table with `path` and an optional `depth`:

- `depth` is how many levels below `path` to search. It must be an integer of at least 1. Depth 1
  lists the immediate subdirectories of `path`; depth 2 also lists their subdirectories, and so on.
- `$VARS` and a leading `~` are expanded, so one config can be shared across machines.
- Roots that don't exist are ignored.
- A directory containing `.git` is listed as a project and its children are not searched. A
  checkout nested inside another project will not appear.
- Hidden directories (names starting with `.`) and symlinks are skipped.
- A project found by more than one root is listed once.

If there is no config file, `~/projects` is searched at depth 1. Once a config file exists, only the
`roots` it lists are searched. No defaults are added, so a config without `roots` finds no projects.

### `[slot.NAME]`

A slot is a named command that runs once per tmux session. Running it again focuses the existing
window or pane instead of starting a second copy.

- `NAME` may contain only letters, digits, `-` and `_`.
- `command` is required. It runs in the project directory of the session you start it from, or in
  the current directory if the session isn't a project.
- `placement = "window"` creates a detached window for the slot and selects it on later runs.
- `placement = "pane"` splits the session's current window and selects the pane on later runs.
  `split = "right"` splits side by side; `split = "below"` splits top and bottom.
- Slots are matched by tmux user options set when they're created. A window or pane you
  create by hand with the same name is not treated as a slot.
- When the command exits, its window or pane normally closes (tmux's default). Running the slot
  again starts it fresh.
- `tmux-project-switcher run NAME` works only inside a tmux session. `tmux-project-switcher slots`
  lists the configured slots.

### Discovery and session names

- Projects shown in the picker exclude directories that already have an open session.
- Session names come from directory names, with `.`, `:` and whitespace replaced by `_`
  (so `my.app` becomes `my_app`). A name already used by a different path gets a `-2`, `-3`, ... suffix.

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
