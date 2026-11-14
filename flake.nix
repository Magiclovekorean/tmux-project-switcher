{
  description = "Jump between project directories and tmux sessions with fzf";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (pkgs: {
        default = pkgs.python3Packages.buildPythonApplication {
          pname = "tmux-project-switcher";
          version = "0.1.0";
          pyproject = true;
          src = ./.;

          build-system = [ pkgs.python3Packages.setuptools ];
          nativeBuildInputs = [ pkgs.makeWrapper ];

          # tmux and fzf are runtime dependencies. Suffix them to PATH so that a
          # tmux/fzf the user already has (which matches their running server) wins.
          postFixup = ''
            wrapProgram $out/bin/tmux-project-switcher \
              --suffix PATH : ${pkgs.lib.makeBinPath [ pkgs.tmux pkgs.fzf ]}
          '';

          checkPhase = ''
            runHook preCheck
            python -m unittest discover -s tests
            runHook postCheck
          '';

          meta = {
            description = "Jump between project directories and tmux sessions with fzf";
            mainProgram = "tmux-project-switcher";
            homepage = "https://github.com/Magiclovekorean/tmux-project-switcher";
            license = pkgs.lib.licenses.mit;
          };
        };
      });

      apps = forAllSystems (pkgs: {
        default = {
          type = "app";
          program = "${self.packages.${pkgs.system}.default}/bin/tmux-project-switcher";
        };
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (ps: [ ]))
            pkgs.tmux
            pkgs.fzf
          ];
          shellHook = ''
            export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
          '';
        };
      });
    };
}
