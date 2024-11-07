import re
from io import StringIO
from os import environ, getcwd
from os.path import join, isfile, realpath, expanduser, abspath, sep
from gnureadline import (parse_and_bind, set_completer, read_history_file, write_history_file,
                         clear_history)
from argparse import ArgumentParser
from contextlib import contextmanager
from signal import signal, SIGINT, SIGALRM, setitimer, ITIMER_REAL
from textwrap import dedent
from functools import partial
from sys import _getframe, stderr
from pdb import Pdb

from lark import Lark
from lark.visitors import Interpreter

from sm_aicli import *


REVISION:str|None
try:
  REVISION=environ["AICLI_REVISION"]
except Exception:
  try:
    from subprocess import check_output, DEVNULL
    REVISION=check_output(['git', 'rev-parse', 'HEAD'],
                          cwd=environ['AICLI_ROOT'],
                          stderr=DEVNULL).decode().strip()
  except Exception:
    try:
      from sm_aicli.revision import REVISION as __rv__
      REVISION = __rv__
    except ImportError:
      REVISION = None

VERSION:str|None
try:
  VERSION=check_output(['python3', 'setup.py', '--version'],
                       cwd=environ['AICLI_ROOT'],
                       stderr=DEVNULL).decode().strip()
except Exception:
  try:
    from sm_aicli.revision import VERSION as __ver__
    VERSION = __ver__
  except ImportError:
    VERSION = None

def _get_cmd_prefix():
  prefices = list({c[0] for c in COMMANDS if len(c)>0})
  assert len(prefices) == 1
  return prefices[0]

CMDPREFIX = _get_cmd_prefix()

ARG_PARSER = ArgumentParser(description="Command-line arguments")
ARG_PARSER.add_argument(
  "--model-dir",
  type=str,
  help="Model directory to prepend to model file names",
  default='.'
)
ARG_PARSER.add_argument(
  "--image-dir",
  type=str,
  help="Directory in which to store images",
  default='.'
)
ARG_PARSER.add_argument(
  "--model", "-m",
  type=str,
  help="Model to use. STR1 is 'gpt4all' (the default) or 'openai'. STR2 is the model name",
  metavar="[STR1:]STR2",
  # default="mistral-7b-instruct-v0.1.Q4_0.gguf",
  # default='/home/grwlf/.local/share/nomic.ai/GPT4All/Meta-Llama-3-8B-Instruct.Q4_0.gguf'
  default=None
)
ARG_PARSER.add_argument(
  "--num-threads", "-t",
  type=int,
  help="Number of threads to use",
  default=None
)
ARG_PARSER.add_argument(
  '--model-apikey',
  type=str,
  help="Model provider-specific API key",
  metavar="STR",
  default=None
)
ARG_PARSER.add_argument(
  "--model-temperature",
  type=float,
  help="Temperature parameter of the model",
  default=None
)
ARG_PARSER.add_argument(
  "--device", "-d",
  type=str,
  help="Device to use for chatbot, e.g. gpu, amd, nvidia, intel. Defaults to CPU",
  default=None
)
ARG_PARSER.add_argument(
  "--readline-key-send",
  type=str,
  help="Terminal code to treat as Ctrl+Enter (default: \\C-k)",
  default="\\C-k"
)
ARG_PARSER.add_argument(
  '--readline-prompt', '-p',
  type=str,
  help="Input prompt (default: >>>)",
  default=">>> "
)
HISTORY_DEF="_sm_aicli_history"
ARG_PARSER.add_argument(
  '--readline-history',
  type=str,
  metavar='FILE',
  help=f"History file name (default is '{HISTORY_DEF}'; set empty to disable)",
  default=HISTORY_DEF
)
ARG_PARSER.add_argument(
  '--verbose',
  type=str,
  metavar='NUM',
  help="Set the verbosity level 0-no,1-full",
)
ARG_PARSER.add_argument(
  '--revision',
  action='store_true',
  help="Print the revision",
)
ARG_PARSER.add_argument(
  '--version',
  action='store_true',
  help="Print the version",
)
ARG_PARSER.add_argument(
  '--rc',
  default='_aicli,.aicli,_sm_aicli,.sm_aicli',
  help="List of config file names (','-separated, use empty or 'none' to disable)",
)

def ask_for_comment_as_text(ast:ActorState, cnv:Conversation, aname:ActorName) -> None:
  try:
    actor = ast.actors.get(aname)
    if actor is None:
      raise RuntimeError(f"Actor {actor} does not exist")

    interrupted:bool = False
    def _signal_handler(signum, frame):
      nonlocal interrupted
      actor.interrupt()
      interrupted = True

    comment = ''
    response = actor.text_stream_comment(cnv)
    with with_sigint(_signal_handler):
      for token in response:
        comment += token
        print(token, end='', flush=True)

    if interrupted:
      print("\n<Interrupted>")
    else:
      cnv.utterances.append(Utterance(aname, comment))
  finally:
    print()

def read_configs(args, rcnames:list[str])->list[str]:
  acc = []
  current_dir = abspath(getcwd())
  path_parts = current_dir.split(sep)
  for depth in range(2, len(path_parts) + 1):
    directory = sep.join(path_parts[:depth])
    # for fn in ['_aicli', '.aicli', '_sm_aicli', '.sm_aicli']:
    for fn in rcnames:
      candidate_file = join(directory, fn)
      if isfile(candidate_file):
        with open(candidate_file, 'r') as file:
          info(f"Reading {candidate_file}")
          for line in file.readlines():
            info(line.strip())
            acc.append(line.strip())
  return acc

def get_help_string(arg_parser):
  help_output = StringIO()
  arg_parser.print_help(help_output)
  return help_output.getvalue()

def reload_history(args):
  if args.readline_history:
    try:
      clear_history()
      read_history_file(args.readline_history)
      info(f"History file loaded")
    except FileNotFoundError:
      info(f"History file not loaded")
  else:
    info(f"History file is not used")

def main(cmdline=None):
  args = ARG_PARSER.parse_args(cmdline)
  args.help = get_help_string(ARG_PARSER)
  if args.revision or args.version:
    if args.revision:
      print(REVISION)
    if args.version:
      print(VERSION)
    return 0

  header = StringIO()
  rcnames = environ.get('AICLI_RC', args.rc)
  if rcnames is not None and len(rcnames)>0 and rcnames!='none':
    for line in read_configs(args, rcnames.split(',')):
      header.write(line+'\n')
  else:
    info("Skipping configuration files")
  if args.model is not None:
    header.write(f"/model {ensure_quoted(args.model)}\n")
  if args.model_apikey is not None:
    header.write(f"/apikey {ensure_quoted(args.model_apikey)}\n")
  parse_and_bind('tab: complete')
  parse_and_bind(f'"{args.readline_key_send}": "{CMD_ASK}\n"')
  hint = args.readline_key_send.replace('\\', '')

  print(f"Type /help or a question followed by the /ask command (or by pressing "
        f"`{hint}` key).", file=stderr)

  reload_history(args)

  cnv = Conversation.init()
  st = ActorState.init()
  current_actor = UserName()
  current_modality = Modality.Text
  st.actors[current_actor] = UserActor(UserName(), ActorOptions.init(), args, header.getvalue())

  model_dir = onematch(expanddir(args.model_dir))
  image_dir = onematch(expanddir(args.image_dir))

  while True:
    try:
      utterance = st.actors[current_actor].react(st.get_view(), cnv)
      assert utterance.actor_name == st.actors[current_actor].name, (
        f"{utterance.actor_name} != {st.actors[current_actor].name}"
      )
      cnv.utterances.append(utterance)
      intention = utterance.intention
      if intention.dbg_flag:
        info("Type `cont` to continue when done")
        Pdb(nosigint=True).set_trace(_getframe())
        reload_history(args)
      if intention.actor_updates is not None:
        for name, opt in intention.actor_updates.options.items():
          actor = st.actors.get(name)
          if actor is not None:
            actor.set_options(opt)
          else:
            if name.provider == "openai":
              st.actors[name] = OpenAIActor(name, opt, image_dir=image_dir)
            elif name.provider == "gpt4all":
              st.actors[name] = GPT4AllActor(name, opt, model_dir=model_dir)
            elif name.provider == "dummy":
              st.actors[name] = DummyActor(name, opt)
            else:
              raise RuntimeError(f"Unsupported provider {name.provider}")
      if intention.actor_next is not None:
        assert intention.actor_next in st.actors, (
          f"{intention.actor_next} is not among {st.actors.keys()}"
        )
        current_actor = intention.actor_next
      if intention.reset_flag:
        cnv = Conversation.init()
        for a in st.actors.values():
          a.reset()
      if intention.exit_flag:
        break
    except KeyboardInterrupt:
      info("^C", prefix=False)
      current_actor = UserName()
      current_modality = Modality.Text
    except NotImplementedError as e:
      err("<Not implemented>")
      current_actor = UserName()
      current_modality = Modality.Text
    except ValueError as e:
      err(e)
      current_actor = UserName()
      current_modality = Modality.Text

