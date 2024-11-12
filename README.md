A (yet another) GNU Readline-based application for interaction with chat-oriented AI models.

Supported model providers:

* [OpenAI](https://www.openai.com) via REST API
* [GPT4All](https://www.nomic.ai/gpt4all) via Python bindings

Contents
--------

<!-- vim-markdown-toc GFM -->

* [Install](#install)
    * [Using Pip](#using-pip)
    * [Using Nix](#using-nix)
* [Develop](#develop)
* [Usage](#usage)
    * [Command-line reference](#command-line-reference)
    * [Grammar reference](#grammar-reference)
    * [Example session](#example-session)
* [Vim integration](#vim-integration)
* [Roadmap](#roadmap)

<!-- vim-markdown-toc -->

Install
-------

The following installation options are available:

### Stable release, using Pip

``` sh
$ pip install sm_aicli
```

### Latest version, using Nix

``` sh
$ git clone --depth=1 https://github.com/sergei-mironov/aicli && cd aicli
# Optionally, change the 'nixpkgs' input of the flake.nix to a more suitable
$ nix profile install ".#python-aicli"
```

### Development shell

This project relies on Nix development infrastructure.

``` sh
$ git clone --depth=1 https://github.com/sergei-mironov/aicli && cd aicli
$ nix develop
```

Usage
-----

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
# Commands start with `/`. Use `\/` to process next `/` as a regular text.
escape.3: /\\./
# The commands are:
# /append TYPE:FROM TYPE:TO - Append a file, a buffer or a constant to a file or to a buffer.
# /cat TYPE:WHAT            - Print a file or buffer to STDOUT.
# /cp TYPE:FROM TYPE:TO     - Copy a file, a buffer or a constant into a file or into a buffer.
# /model PROVIDER:NAME      - Set the current model to `model_string`. Allocate the model on first use.
# /read WHERE               - Reads the content of the 'IN' buffer into a special variable.
# /set WHAT                 - Set terminal or model option
# /shell TYPE:FROM          - Run a shell command.
# /clear                    - Clear the buffer named `ref_string`.
# /reset                    - Reset the conversation and all the models
# /version                  - Print version
# /dbg                      - Run the Python debugger
# /echo                     - Echo the following line to STDOUT
# /exit                     - Exit
# /help                     - Print help
command.2: /\/version/ | \
           /\/dbg/ | \
           /\/reset/ | \
           /\/echo/ | \
           /\/ask/ | \
           /\/help/ | \
           /\/exit/ | \
           /\/model/ / +/ model_string | \
           /\/read/ / +/ /model/ / +/ /prompt/ | \
           /\/set/ / +/ (/model/ / +/ (/apikey/ / +/ ref_string | \
                                       (/t/ | /temp/) / +/ (float | def) | \
                                       (/nt/ | /nthreads/) / +/ (number | def) | \
                                       /imgsz/ / +/ string | \
                                       /verbosity/ / +/ (number | def)) | \
                         (/term/ | /terminal/) / +/ (/modality/ / +/ modality_string | \
                                                     /rawbin/ / +/ bool)) | \
           /\/cp/ / +/ ref_string / +/ ref_string | \
           /\/append/ / +/ ref_string / +/ ref_string | \
           /\/cat/ / +/ ref_string | \
           /\/clear/ / +/ ref_string | \
           /\/shell/ / +/ ref_string

# Strings can start and end with a double-quote. Unquoted strings should not contain spaces.
string: "\"" string_quoted "\"" | string_raw
string_quoted: /[^"]+/ -> string_value
string_raw: /[^"][^ \/\n]*/ -> string_value

# Model names have format "PROVIDER:NAME". Model names containing spaces must be double-quoted.
model_string: "\"" model_quoted "\"" | model_raw
model_quoted: (model_provider ":")? string_quoted -> model
model_raw: (model_provider ":")? string_raw -> model
model_provider: "gpt4all" -> mp_gpt4all | "openai" -> mp_openai | "dummy" -> mp_dummy

# Modalities are either `img` or `text`.
modality_string: "\"" modality "\"" | modality
modality: /img/ -> modality_img | /text/ -> modality_text

# References mention either a file (`file:filename`), a buffer (`buffer:a`) or a string constant
# (`verbatim:ABC`).
ref_string: "\"" ref_quoted "\"" | ref_raw
ref_quoted: (ref_schema ":")? string_quoted -> ref
ref_raw: (ref_schema ":")? string_raw -> ref
ref_schema: /verbatim/ | /file/ | /bfile/ | /buffer/ -> ref_schema

# Base token types
filename: string
number: /[0-9]+/
float: /[0-9]+\.[0-9]*/
def: "default"
bool: /true/|/false/|/yes/|/no/|/1/|/0/
text.0: /([^\/#](?!\/|\\))*[^\/#]/s
%ignore /#[^\n]*/
```

By default, the application tries to read configuration files starting from the `/` directory down
to the current directory. The contents of `_aicli`, `.aicli`, `_sm_aicli` and `.sm_aicli` files is
interpreted as commands.

### Example session

``` sh
$ aicli
```

``` txt
INFO: Type /help or a question followed by the /ask command (or by pressing `C-k` key).
>>> /model "./_model/Meta-Llama-3-8B-Instruct.Q4_0.gguf"
>>> Hi!/ask
Hello! I'm happy to help you. What's on your mind?^C
>>> What's your name?/ask
I don't really have a personal name, but you can call me "Assistant"
```

Architecture
------------

In this project we try to keep the code base as small as possible. The main data types are defined
as follows:

<!--
``` python
def class_url(url_template, file_name, entity) -> str:
  line_number = None
  with open(file_name, 'r') as file:
    for i, line in enumerate(file, start=1):
      if f"class {entity}" in line.strip():
        line_number = i
        break
  if line_number is None:
    raise ValueError(f"Class '{entity}' not found in file '{file_name}'.")
  return url_template.replace("%L", str(line_number))

def typelink(entity):
  url_template = './python/sm_aicli/types.py#L%L'
  # url_template = 'https://github.com/sergei-mironov/aicli/blob/v2.0.0/python/sm_aicli/types.py#%L'
  file_name = './python/sm_aicli/types.py'
  url = class_url(url_template, file_name, entity)
  return f"[{entity}]({url})"

print(' | '.join([typelink(x) for x in [
  "Actor", "Conversation", "Utterance", "Intention", "Stream"]
]))
print()
```
-->

<!--result-->
[Actor](./python/sm_aicli/types.py#L28) | [Conversation](./python/sm_aicli/types.py#L6) |
[Utterance](./python/sm_aicli/types.py#L108) | [Intention](./python/sm_aicli/types.py#L59) |
[Stream](./python/sm_aicli/types.py#L75)
<!--noresult-->


Vim integration
---------------

Aicli is supported by the [Litrepl](https://github.com/sergei-mironov/litrepl) text processor.

![Peek 2024-07-19 00-11](https://github.com/user-attachments/assets/7e5e59ea-bb96-4ebe-988f-726e83929dab)


Roadmap
-------

Some thoughts on adding image support:

- [x] App must work with different model providers at once.
- [x] App must provide a common conversation schema and translate it to model provider languages,
  rather than stick to provider's conversation schemas.
- [ ] App must allow to work with different models even for the same modality. A good feature would
  be to re-ask different models to generate response candidate for a given conversation tip. So, a
  conversation editor.

