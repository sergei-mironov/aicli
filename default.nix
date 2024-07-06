{ pkgs
, stdenv ? pkgs.stdenv
} :
let
  local = rec {

    inherit (pkgs) cmake fmt shaderc vulkan-headers vulkan-loader wayland pkg-config;

    python = pkgs.python3;

    gpt4all-src = pkgs.gpt4all.src;

    python-dev = python.withPackages (
      pp:  with pp; [
        tqdm
        requests
        typing-extensions
        importlib-resources
        setuptools
      ]
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
      ];
    };

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


    # TODO: complete the package
    gpt4all-cli = (py: py.buildPythonApplication rec {
      pname = "gpt4all-cli";
      inherit (pkgs.gpt4all) version src;

      propagatedBuildInputs = [(gpt4all-bindings py.pkgs)];
    });


    python-gpt4all-bindings = python.withPackages (
      pp:  with pp; [
        (gpt4all-bindings pp)
      ]
    );

    python-gpt4all-bindings-dev = python.withPackages (
      pp:  with pp; [
        ipython
        (gpt4all-bindings pp)
        typer
      ]
    );

    collection = rec {
      inherit shell gpt4all-src gpt4all-backend python-gpt4all-bindings
              python-gpt4all-bindings-dev;
    };
  };

in
  local.collection

