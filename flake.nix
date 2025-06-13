{
  description = "GPT4all cli project";

  nixConfig = {
    bash-prompt = "\[ aicli \\w \]$ ";
  };

  inputs = {
    nixpkgs = {
      # url = "git+file:/home/nixcfg/nixpkgs/";
      # Author's favorite nixpkgs
      url = "github:grwlf/nixpkgs/local17.2";
    };

    # litrepl = {
    #   url = "git+file:/home/grwlf/proj/litrepl.vim/";
    # };
  };

  outputs = { self, nixpkgs }:
    let
      defaults = system : (import ./default.nix) {
        pkgs = import nixpkgs { inherit system; };
        revision = if self ? rev then self.rev else null;
      };
      defaults-x86_64 = defaults "x86_64-linux";
      defaults-aarch64 = defaults "aarch64-linux";
    in {
      packages = {
        x86_64-linux = defaults-x86_64;
        aarch64-linux = defaults-aarch64;
      };
      devShells = {
        x86_64-linux = { default = defaults-x86_64.shell; };
        aarch64-linux = { default = defaults-aarch64.shell; };
      };
    };

}
