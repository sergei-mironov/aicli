A (yet another) GNU Readline-based application for interacting with chat-oriented AI models.

Features
--------

This application is designed with a focus on minimizing code size. As a Unix-style program, it can
be used both as an interactive terminal with command completion or as a shebang script runner.

Supported model providers:

* [OpenAI](https://www.openai.com) via REST API. We tested the text `gpt-4o` model and the graphic
  `dall-e-2` and `dall-e-3` models.
* [GPT4All](https://www.nomic.ai/gpt4all) via Python bindings

The scripting language allows basic processing involving buffer variables and file manipulaitons.
For advanced scripting, we suggest using text session management tools such as
[Expect](https://core.tcl-lang.org/expect/index) or
[Litrepl](https://github.com/sergei-mironov/litrepl) (by the same author).

Contents
--------

<!-- vim-markdown-toc GFM -->

* [Install](#install)
    * [Stable release](#stable-release)
    * [Latest or development version](#latest-or-development-version)
        * [Latest version using Pip](#latest-version-using-pip)
        * [Latest version using Nix](#latest-version-using-nix)
        * [Development shell](#development-shell)
* [Quick start](#quick-start)
* [Reference](#reference)
    * [Command-line reference](#command-line-reference)
    * [Commands overview](#commands-overview)
    * [Grammar reference](#grammar-reference)
* [Architecture](#architecture)
* [Vim integration](#vim-integration)
* [Roadmap](#roadmap)

<!-- vim-markdown-toc -->

Install
-------

The following installation options are available:

### Stable release

You can install the stable release of the project using Pip, a default package manager for Python.

``` sh
$ pip install sm_aicli
```

### Latest or development version

#### Latest version using Pip

To install the latest version of `sm_aicli` directly from the GitHub repository, you can use Pip
with the Git URL.

``` sh
$ pip install git+https://github.com/sergei-mironov/aicli.git
```

#### Latest version using Nix

To install the latest version of `aicli` using Nix, you first need to clone the repository. Nix will
automatically manage and bring in all necessary dependencies, ensuring a seamless installation
experience.

``` sh
$ git clone --depth=1 https://github.com/sergei-mironov/aicli && cd aicli
# Optionally, change the 'nixpkgs' input of the flake.nix to a more suitable
$ nix profile install ".#python-aicli"
```

#### Development shell

Set up a development environment using Nix to work on the project. Clone the repository and activate
the development shell with the following commands:

``` sh
$ git clone --depth=1 https://github.com/sergei-mironov/aicli && cd aicli
$ nix develop
```

Quick start
-----------

Below is a simple OpenAI terminal session. The commands start with `/`, while lines following `#`
are ignored. Other text is collected into a buffer and is sent to the model by the `/ask` command.
Please replace `YOUR_API_KEY` with your actual API key.

``` sh
$ aicli
>>> /model openai:"gpt-4o"
>>> /set model apikey verbatim:YOUR_API_KEY # <--- Your OpenAI API key goes here
# Other option here is:
# /set model apikey file:"/path/to/your/openai/apikey"
>>> Tell me about monkeys
>>> /ask

Monkeys are fascinating primates that belong to two main groups: New World monkeys and
Old World monkeys. Here's a brief overview of ...
```

The last model answer is recorded into the `out` buffer. Let's print it again and save it to a file
using the `/cp` command:

``` sh
>>> /cat buffer:out
..
>>> /cp buffer:out file:monkey.txt
```

The [ai](./ai) folder contains script examples illustrating command usage.

Reference
---------

### Command-line reference

<!--
``` python
!aicli --help
```
-->
``` result
usage: aicli [-h] [--model-dir MODEL_DIR] [--image-dir IMAGE_DIR]
             [--model [STR1:]STR2] [--num-threads NUM_THREADS]
             [--model-apikey STR] [--model-temperature MODEL_TEMPERATURE]
             [--device DEVICE] [--readline-key-send READLINE_KEY_SEND]
             [--readline-prompt READLINE_PROMPT] [--readline-history FILE]
             [--verbose NUM] [--revision] [--version] [--rc RC] [-K]
             [filenames ...]

Command-line arguments

positional arguments:
  filenames             List of filenames to process

options:
  -h, --help            show this help message and exit
  --model-dir MODEL_DIR
                        Model directory to prepend to model file names
  --image-dir IMAGE_DIR
                        Directory in which to store images
  --model [STR1:]STR2, -m [STR1:]STR2
                        Model to use. STR1 is 'gpt4all' (the default) or
                        'openai'. STR2 is the model name
  --num-threads NUM_THREADS, -t NUM_THREADS
                        Number of threads to use
  --model-apikey STR    Model provider-specific API key
  --model-temperature MODEL_TEMPERATURE
                        Temperature parameter of the model
  --device DEVICE, -d DEVICE
                        Device to use for chatbot, e.g. gpu, amd, nvidia,
                        intel. Defaults to CPU
  --readline-key-send READLINE_KEY_SEND
                        Terminal code to treat as Ctrl+Enter (default: \C-k)
  --readline-prompt READLINE_PROMPT, -p READLINE_PROMPT
                        Input prompt (default: >>>)
  --readline-history FILE
                        History file name (default is '_sm_aicli_history'; set
                        empty to disable)
  --verbose NUM         Set the verbosity level 0-no,1-full
  --revision            Print the revision
  --version             Print the version
  --rc RC               List of config file names (','-separated, use empty or
                        'none' to disable)
  -K, --keep-running    Open interactive shell after processing all positional
                        arguments
```

### Commands overview

<!--
``` python
from sm_aicli.actor.user import *
print("| Command         | Arguments       | Description |")
print("|:----------------|:----------------|-------------|")
for command, (arguments, description) in CMDHELP.items():
  print(f"| {command:15s} | {arguments:15s} | {description} |")
```
-->


<!--result-->
| Command         | Arguments       | Description |
|:----------------|:----------------|-------------|
| /append         | REF REF         | Append a file, a buffer or a constant to a file or to a buffer. |
| /cat            | REF             | Print a file or buffer to STDOUT. |
| /cd             | REF             | Change the current directory to the specified path |
| /clear          |                 | Clear the buffer named `ref_string`. |
| /cp             | REF REF         | Copy a file, a buffer or a constant into a file or into a buffer. |
| /dbg            |                 | Run the Python debugger |
| /echo           |                 | Echo the following line to STDOUT |
| /exit           |                 | Exit |
| /help           |                 | Print help |
| /model          | PROVIDER:NAME   | Set the current model to `model_string`. Allocate the model on first use. |
| /paste          | BOOL            | Enable or disable paste mode. |
| /read           | WHERE           | Reads the content of the 'IN' buffer into a special variable. |
| /reset          |                 | Reset the conversation and all the models |
| /set            | WHAT            | Set terminal or model option, check the Grammar for a full list of options. |
| /shell          | REF             | Run a system shell command. |
| /version        |                 | Print version |
<!--noresult-->


### Grammar reference

The console accepts a language defined by the following grammar:

<!--
``` python
from sm_aicli import GRAMMAR
from textwrap import dedent
print(dedent(GRAMMAR).strip())
```
-->

``` result
start: (command | escape | text)? (command | escape | text)*
text: TEXT
escape: ESCAPE
# Commands start with `/`. Use `\/` to process next `/` as a regular text.
# The commands are:
command.1: /\/version/ | \
           /\/dbg/ | \
           /\/reset/ | \
           /\/echo/ | \
           /\/ask/ | \
           /\/help/ | \
           /\/exit/ | \
           /\/model/ / +/ model_ref | \
           /\/read/ / +/ /model/ / +/ /prompt/ | \
           /\/set/ / +/ (/model/ / +/ (/apikey/ / +/ ref | \
                                       (/t/ | /temp/) / +/ (FLOAT | DEF) | \
                                       (/nt/ | /nthreads/) / +/ (NUMBER | DEF) | \
                                       /imgsz/ / +/ string | \
                                       /verbosity/ / +/ (NUMBER | DEF)) | \
                             (/term/ | /terminal/) / +/ (/modality/ / +/ MODALITY | \
                                                         /rawbin/ / +/ BOOL | \
                                                         /prompt/ / +/ string | \
                                                         /width/ / +/ (NUMBER | DEF))) | \
           /\/cp/ / +/ ref / +/ ref | \
           /\/append/ / +/ ref / +/ ref | \
           /\/cat/ / +/ ref | \
           /\/clear/ / +/ ref | \
           /\/shell/ / +/ ref | \
           /\/cd/ / +/ ref | \
           /\/paste/ / +/ BOOL

# Strings can start and end with a double-quote. Unquoted strings should not contain spaces.
string: "\"" string_quoted "\"" | string_unquoted
string_quoted: STRING_QUOTED -> string_value
string_unquoted: STRING_UNQUOTED -> string_value

model_ref: (PROVIDER ":")? string

# References mention locations which could be either a file (`file:path/to/file`), a binary file
# (`bfile:path/to/file`), a named memory buffer (`buffer:name`) or a read-only string constant
# (`verbatim:ABC`).
ref: (SCHEMA ":")? string -> ref | \
     /file/ (/\(/ | /\(/ / +/) ref (/\)/ | / +/ /\)/) -> ref_file

# Base token types
ESCAPE.5: /\\./
SCHEMA.4: /verbatim/|/file/|/bfile/|/buffer/
PROVIDER.4: /openai/|/gpt4all/|/dummy/
STRING_QUOTED.3: /[^"]+/
STRING_UNQUOTED.3: /[^"\(\)][^ \(\)\n]*/
TEXT.0: /([^#](?!\/))*[^\/#]/s
NUMBER: /[0-9]+/
FLOAT: /[0-9]+\.[0-9]*/
DEF: "default"
BOOL: /true/|/false/|/yes/|/no/|/on/|/off/|/1/|/0/
MODALITY: /img/ | /text/
%ignore /#[^\n]*/
```

By default, the application tries to read configuration files starting from the `/` directory down
to the current directory. The contents of `_aicli`, `.aicli`, `_sm_aicli` and `.sm_aicli` files is
interpreted as commands.

Architecture
------------

<!--``` python
%%bash
mdlink.py --file ./python/sm_aicli/types.py \
    Conversation Utterance Actor Intention Stream
```-->

<!--result-->
[Conversation](./python/sm_aicli/types.py#L6) | [Utterance](./python/sm_aicli/types.py#L109) | [Actor](./python/sm_aicli/types.py#L28) | [Intention](./python/sm_aicli/types.py#L60) | [Stream](./python/sm_aicli/types.py#L76)

<!--noresult-->

In this project, we aim to keep the codebase as compact as possible. All data types are defined in a
single file, [types.py](./python/sm_aicli/types.py), while the rest of the project is dedicated to
implementing algorithms. The **Conversation** abstraction plays a central role.

The main loop of the program manages **Actors**, who add utterances to the stack of existing ones.
The entire design emulates Free Monad evaluation, with **Utterance** representing the Free Monad
itself. Most of the monad constructors are represented as flags within the **Intention** part of the
Utterance. By using these flags, an actor can request the introduction of additional actors into the
conversation.

<!--``` python
%%bash
docpic.py '60%' <<"EOF"
\begin{tikzcd}
                                       & Conversation &                                                \\
                                       &              &                                                \\
Actor \arrow[rr, "related", bend left] &              & {Actor,Utterance} \arrow[ll, "new", bend left]
\end{tikzcd}
EOF
```-->

<p align='center'>
<!--result-->
<img src="doc/b8760ee5e0.svg" width="60%" />
<!--noresult-->
</p>

The user-facing terminal actor utilizes the same API to generate utterances during the
interpretation of input language. The language parser is generated by the Lark library from a
predefined [grammar](#commands-overview).

Each actor receives a read-only view of the Conversation, identifies the related Utterance, and then
takes responsibility for decoding it into the appropriate third-party format, computing the
response, and encoding it back into the Utterance. A popular choice is the
`{'role':'system'|'assistant'|'user', 'content': str}` structure used by the OpenAI API.

<!--``` python
%%bash
docpic.py '60%' <<"EOF"
% https://tikzcd.yichuanshen.de/#N4Igdg9gJgpgziAXAbVABwnAlgFyxMJZABgBoBGAXVJADcBDAGwFcYkQBBAYxwgCcQAX1LpMufIRQAmCtTpNW7brz6kAqjhww+9MFzbDR2PASIypchizaIQGrTr0wA5EJEgMxiUXKlilhRsQAGECWm04ehNCQTkYKABzeCJQADM+CABbJDIQXiRfeWt2PhhGKPi3NIzsxEL8xBkixVtSuAwwKCqQdKykJobcqxa8+j4knCFKQSA
\begin{tikzcd}
                            & Conversation &                                        \\
Actor \arrow[rr, "related"] &              & {Actor,Utterance} \arrow[d, "respond"] \\
                            &              & Utterance' \arrow[llu, "target"]      
\end{tikzcd}
EOF
```-->

<p align='center'>
<!--result-->
<img src="doc/6221aa1ec0.svg" width="60%" />
<!--noresult-->
</p>

Vim integration
---------------

Aicli is supported by the [Litrepl](https://github.com/sergei-mironov/litrepl) text processor.

![Peek 2024-07-19 00-11](https://github.com/user-attachments/assets/7e5e59ea-bb96-4ebe-988f-726e83929dab)

Roadmap
-------

* Core functionality:
  * [x] OpenAI graphic API models
  - [ ] Antropic API
  - [ ] OpenAI tooling API subset
  - [ ] Advanced scripting: functions

* Usability:
  - [x] Command completion in terminal.
  - [x] `/shell` running a system shell command.
  - [ ] Encode errors into the Conversation to allow actors to process them.
  - [ ] `/set terminal width INT` for limiting text width for better readability.
  - [ ] `/edit` for running an editor.
  - [ ] `/set model alias REF` for setting a short name for a model.
  - [ ] Session replay.

