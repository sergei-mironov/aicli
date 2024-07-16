A simple GNU Readline-based application for interaction with chat-oriented AI models using
[GPT4All](https://www.nomic.ai/gpt4all) Python bindings.

Contents
--------

<!-- vim-markdown-toc GFM -->

* [Install](#install)
    * [Pip](#pip)
    * [Nix](#nix)
* [Usage](#usage)
    * [Example session](#example-session)

<!-- vim-markdown-toc -->

Install
-------

The following installation options are available:

### Pip

```sh
$ pip install git+https://github.com/sergei-mironov/gpt4all-cli.git
```

Note: `pip install gpt4all-cli` might also work, but the `git+https` method would bring the most
recent version.

### Nix

```sh
$ git clone --depth=1 https://github.com/sergei-mironov/gpt4all-cli && cd gpt4all-cli
# Optionally, change the 'nixpkgs' input of the flake.nix to a more suitable
$ nix profile install ".#python-gpt4all-cli"
```

Usage
-----

<!--
``` python
!gpt4all-cli --help
```
-->
``` result
usage: gpt4all-cli [-h] [--model MODEL] [--num-threads NUM_THREADS]
                   [--device DEVICE] [--readline-key-send READLINE_KEY_SEND]
                   [--readline-prompt READLINE_PROMPT] [--revision]

Command-line arguments

options:
  -h, --help            show this help message and exit
  --model MODEL, -m MODEL
                        Model to use for chatbot
  --num-threads NUM_THREADS, -t NUM_THREADS
                        Number of threads to use for chatbot
  --device DEVICE, -d DEVICE
                        Device to use for chatbot, e.g. gpu, amd, nvidia,
                        intel. Defaults to CPU.
  --readline-key-send READLINE_KEY_SEND
                        Terminal code to treat as Ctrl+Enter (default: \C-k)
  --readline-prompt READLINE_PROMPT
                        Input prompt (default: >>>)
  --revision            Print the revision
```

### Example session

``` sh
$ gpt4all-cli
```
``` txt
Type /help or a question followed by the /ask command (or by pressing `C-k` key).
>>> /model "~/.local/share/nomic.ai/GPT4All/Meta-Llama-3-8B-Instruct.Q4_0.gguf"
>>> Hi!
>>> /ask
Hello! I'm happy to help you. What's on your mind?^C
>>> What's your name?
>>> /ask
I don't really have a personal name, but you can call me "Assistant"
```

