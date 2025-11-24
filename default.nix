{ pkgs
, stdenv ? pkgs.stdenv
, litrepl
, revision ? null
} :
let
  local = rec {

    inherit (pkgs) cmake fmt shaderc vulkan-headers vulkan-loader wayland
                   pkg-config expect fim pdf2svg pandoc;
    inherit (pkgs.lib) fileContents;

    python = pkgs.python312;

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


    aicli = (pp: pp.buildPythonApplication rec {
      pname = "aicli";
      version = fileContents "${src}/semver.txt";
      format = "setuptools";
      src = ./.;
      nativeBuildInputs = with pp; [ pkgs.git ];
      propagatedBuildInputs = with pp; [
        (gpt4all-bindings pp) gnureadline lark openai pillow socksio
      ];
      AICLI_REVISION = revision;
      AICLI_ROOT = src;
      AICLI_GPT4ALL = "gpt4all-bindings";
      doCheck = true;
      nativeCheckInputs = with pp; [
        pytestCheckHook
      ];
      pythonImportsCheck = [
        "sm_aicli"
      ];
    });

    python-dev = python.withPackages (
      pp: let
        pylsp = pp.python-lsp-server;
        pylsp-mypy = pp.pylsp-mypy.override { python-lsp-server=pylsp; };
      in with pp; [
        pylsp
        pylsp-mypy
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
        openai
        hypothesis
        pillow
        socksio
      ]
    );

    python-aicli = aicli python.pkgs;

    texlive-dev =
      (let
        texlive = pkgs.texlive;
      in
        texlive.combine {
          scheme-medium = texlive.scheme-medium;
          inherit (texlive) pgfopts pgf tikz-cd tikzsymbols standalone;
        }
      );

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
        expect
        fim
        texlive-dev
        pdf2svg
        pandoc
        litrepl.litrepl-release
      ];

      shellHook = with pkgs; ''
        export VIM_LITREPL=${litrepl.vim-litrepl-release}
        if test -f ./env.sh ; then
          . ./env.sh
        fi
      '';
    };

    openai-src = python.pkgs.openai.src;

    collection = rec {
      inherit shell gpt4all-src gpt4all-backend aicli python-dev python-aicli
              openai-src;
    };
  };

in
  local.collection

