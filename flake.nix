{
  description = "GPT4all cli project";

  nixConfig = {
    bash-prompt = "\[ gpt4all-cli \\w \]$ ";
  };

  inputs = {
    nixpkgs = {
      # Author's favorite nixpkgs
      url = "github:grwlf/nixpkgs/local17";
    };

    litrepl = {
      url = "git+file:/home/grwlf/proj/litrepl.vim/";
    };
  };

  outputs = { self, nixpkgs, litrepl }:
    let
      defaults = (import ./default.nix) {
        pkgs = import nixpkgs { system = "x86_64-linux"; };
        litrepl = litrepl.outputs.packages."x86_64-linux";
      };
    in {
      packages = {
        x86_64-linux = defaults;
      };
      devShells = {
        x86_64-linux = {
          default = defaults.shell;
        };
      };
    };

}
