{ pkgs
, stdenv ? pkgs.stdenv
# , litrepl
, revision ? null
} :
let
  local = rec {

    inherit (pkgs) cmake fmt shaderc vulkan-headers vulkan-loader wayland pkg-config;

    python = pkgs.python3;

    gpt4all-src = pkgs.gpt4all.src;

    gpt4all-backend = stdenv.mkDerivation (finalAttrs: {
      pname = "gpt4all-backend";
      inherit (pkgs.gpt4all) version src;

      sourceRoot = "${finalAttrs.src.name}/gpt4all-backend";

      nativeBuildInputs = [
        cmake
      ];

      buildInputs = [
        fmt
        shaderc
        vulkan-headers
        vulkan-loader
        wayland
        pkg-config
      ];

      installPhase = ''
        cp -rv . $out
      '';

      cmakeFlags = [
        "-DKOMPUTE_OPT_USE_BUILT_IN_VULKAN_HEADER=OFF"
        "-DKOMPUTE_OPT_DISABLE_VULKAN_VERSION_CHECK=ON"
        "-DKOMPUTE_OPT_USE_BUILT_IN_FMT=OFF"
      ];
    });


    gpt4all-bindings = (py: py.buildPythonPackage rec {
      pname = "gpt4all-bindings";
      inherit (pkgs.gpt4all) version src;

      format = "setuptools";

      dontUseCmakeConfigure = true;

      preBuild = ''
        cd gpt4all-backend
        mkdir build
        cp -rv ${gpt4all-backend} build
        chmod -R +w build
        cd ../gpt4all-bindings/python
      '';

      nativeBuildInputs = with py; [
        pytest
      ];

      buildInputs = [
        fmt
        shaderc
        vulkan-headers
        vulkan-loader
        wayland
        pkg-config
      ];

      propagatedBuildInputs = with py; [
        tqdm
        requests
        typing-extensions
        importlib-resources
      ];

    });


    gpt4all-cli = (pp: pp.buildPythonApplication rec {
      pname = "gpt4all-cli";
      version = "0.0.1";
      format = "setuptools";
      src = ./.;
      nativeBuildInputs = with pp; [ pkgs.git ];
      propagatedBuildInputs = with pp; [(gpt4all-bindings pp) gnureadline lark];
      GPT4ALLCLI_REVISION = revision;
      GPT4ALLCLI_ROOT = src;
      doCheck = true;
      nativeCheckInputs = with pp; [
        pytestCheckHook
      ];
      pythonImportsCheck = [
        "gpt4all_cli"
      ];
    });


    python-dev = python.withPackages (
      pp:  with pp; [
        tqdm
        requests
        typing-extensions
        importlib-resources
        setuptools
        pytest
        wheel
        twine
        gnureadline
        lark
        ipython
        (gpt4all-bindings pp)
      ]
    );

    python-gpt4all-cli = gpt4all-cli python.pkgs;

    shell = pkgs.mkShell {
      name = "shell";
      buildInputs = [
        cmake
        fmt
        shaderc
        vulkan-headers
        vulkan-loader
        wayland
        pkg-config
        python-dev
        # litrepl.litrepl-release
      ];

      shellHook = with pkgs; ''
        if test -f ./env.sh ; then
          . ./env.sh
        fi
      '';
    };

    collection = rec {
      inherit shell gpt4all-src gpt4all-backend gpt4all-cli python-dev python-gpt4all-cli;
    };
  };

in
  local.collection

