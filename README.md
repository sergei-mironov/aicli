A simple GNU readline-based command-line application for interaction with GPT model using
[GPT4All](https://www.nomic.ai/gpt4all) Python bindings.

<!-- vim-markdown-toc GFM -->

* [Install](#install)
    * [Using Pip](#using-pip)
    * [Using Nix](#using-nix)
* [Usage](#usage)
    * [Example session](#example-session)

<!-- vim-markdown-toc -->

Install
-------

The following installation options are available:

### Using Pip

```sh
$ pip install gpt4all-cli
```

### Using Nix

```sh
$ git clone https://github.com/sergei-mironov/gpt4all-cli
$ cd gpt4all-cli
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
                   [--device DEVICE]
                   [--readline-ctrl-enter READLINE_CTRL_ENTER] [--no-prompts]

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
  --readline-ctrl-enter READLINE_CTRL_ENTER
                        Terminal code to treat as Ctrl+Enter (default: \C-k)
  --no-prompts          Disable prompts
```

### Example session

``` sh
[ gpt4all-cli ]$ gpt4all-cli --model=~/.local/share/nomic.ai/GPT4All/Meta-Llama-3-8B-Instruct.Q4_0.gguf
```
``` txt
>>> Hi!
>>> /ask
Hello! I'm happy to help you. What's on your mind?^C
>>> What's your name?
>>> /ask
I don't really have a personal name, but you can call me "Assistant"
```

