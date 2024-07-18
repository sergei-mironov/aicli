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
usage: gpt4all-cli [-h] [--model-dir MODEL_DIR] [--model MODEL]
                   [--num-threads NUM_THREADS] [--device DEVICE]
                   [--readline-key-send READLINE_KEY_SEND]
                   [--readline-prompt READLINE_PROMPT] [--revision]

Command-line arguments

options:
  -h, --help            show this help message and exit
  --model-dir MODEL_DIR
                        Model directory to prepend to model file names
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

The console accepts language defined by the following grammar:

<!--
``` python
from gpt4all_cli import GRAMMAR
from textwrap import dedent
print(dedent(GRAMMAR).strip())
```
-->

``` result
start: (command | escape | text)? (command | escape | text)*
escape.3: /\\./
command.2: /\/reset|\/ask|\/help|\/exit/ | \
           /\/model/ / +/ string | \
           /\/nthreads/ / +/ number | \
           /\/echo/ | /\/echo/ / /
string: /"[^\"]+"/ | /""/
number: /[1-9][0-9]*/
text: /(.(?!\/|\\))*./s
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

Vim integration
---------------

Gpt4all-cli is supported by the [Litrepl](https://github.com/sergei-mironov/litrepl) text processor.

![Peek 2024-07-19 00-11](https://github.com/user-attachments/assets/7e5e59ea-bb96-4ebe-988f-726e83929dab)
