Usage
-----

``` sh
$ nix build '.#gpt4all-src' --out-link result-src
$ nix build '.#python-gpt4all-bindings-dev'
./result/bin/python ./result-src/gpt4all-bindings/cli/app.py repl [--model=path/to/model]
```
