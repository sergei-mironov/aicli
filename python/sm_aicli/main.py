import re
from io import StringIO
from os import environ, getcwd
from os.path import join, isfile, realpath, expanduser, abspath, sep
from gnureadline import parse_and_bind, set_completer, read_history_file, write_history_file
from argparse import ArgumentParser
from contextlib import contextmanager
from signal import signal, SIGINT, SIGALRM, setitimer, ITIMER_REAL
from textwrap import dedent
from functools import partial

from lark import Lark
from lark.visitors import Interpreter

from sm_aicli import *

no_model_is_active = "No model is active, use /model first"

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
  default=None
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
  '--readline-prompt',
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
  '--no-rc',
  action='store_true',
  help="Do not read configuration files",
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

# def askimg(args, model:Model, message:str) -> None:
#   opt:Options = Options(verbose=as_int(args.verbose, 0))
#   model.set_temperature(as_float(args.model_temperature,None))
#   path = model.ask_image(message, opt=opt)
#   print(path)

# @contextmanager
# def with_chat_session(model:Model):
#   if model is None:
#     yield
#   else:
#     with model.with_chat_session():
#       yield

def ensure_quoted(s:str)->str:
  if not (len(s)>0 and s[0]=='"'):
    s = '"' + s
  if not (len(s)>0 and s[-1]=='"'):
    s = s + '"'
  return s

# def parse_model(args) -> tuple[ModelName] | None:
#   if args.model is None:
#     return None
#   else:
#     mprov,mname = args.model
#     if mprov == 'gpt4all':
#       filename = None
#       for f in model_locations(args, mname):
#         if isfile(f):
#           filename = f
#           break
#       mname = filename if filename is not None else mname
#       return GPT4AllModel(mname, device=args.device)
#     elif mprov == 'openai':
#       apikey = parse_apikey(args)
#       if apikey is None:
#         raise ValueError("OpenAI models require apikey")
#       return OpenAIModel(model=mname, apikey=apikey)
#     elif mprov == 'dummy':
#       apikey = parse_apikey(args)
#       return DummyModel(model=mname, apikey=apikey)
#     else:
#       raise ValueError(f"Invalid model provider '{mprov}'")

def read_configs(args)->list[str]:
  acc = []
  current_dir = abspath(getcwd())
  path_parts = current_dir.split(sep)
  for depth in range(2, len(path_parts) + 1):
    directory = sep.join(path_parts[:depth])
    for fn in ['_aicli', '.aicli', '_sm_aicli', '.sm_aicli']:
      candidate_file = join(directory, fn)
      if isfile(candidate_file):
        with open(candidate_file, 'r') as file:
          print_aux(f"Reading {candidate_file}")
          for line in file.readlines():
            print_aux(line.strip())
            acc.append(line.strip())
  return acc


# def apply_options(args, st:State) -> None:
#   mname = st.current_model_name
#   if mname is None:
#     raise RuntimeError(no_model_is_active)
#   mopt = st.options.get(mname, ModelOptions.init())
#   model = st.models.get(mname)
#   if model is None:
#     if mname.provider == "openai":
#       model = OpenAIModel(mname)
#     elif mname.provider == "gpt4all":
#       model = GPT4AllModel(mname)
#     elif mname.provider == "dummy":
#       model = DummyModel(mname)
#     else:
#       raise ValueError(f"Unknown model provider {mname.provider}")
#   model.set_options(mopt)


def get_help_string(arg_parser):
  help_output = StringIO()
  arg_parser.print_help(help_output)
  return help_output.getvalue()

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
  if not environ.get('AICLI_NORC') and not args.no_rc:
    for line in read_configs(args):
      header.write(line+'\n')
  else:
    print_aux("Skipping reading configuration files")
  if args.model is not None:
    header.write(f"/model {ensure_quoted(args.model)}\n")
  if args.model_apikey is not None:
    header.write(f"/apikey {ensure_quoted(args.model_apikey)}\n")
  parse_and_bind('tab: complete')
  parse_and_bind(f'"{args.readline_key_send}": "{CMD_ASK}\n"')
  hint = args.readline_key_send.replace('\\', '')

  print(f"Type /help or a question followed by the /ask command (or by pressing "
        f"`{hint}` key).")

  if args.readline_history:
    try:
      read_history_file(args.readline_history)
      print_aux(f"History file loaded")
    except FileNotFoundError:
      print_aux(f"History file not loaded")
  else:
    print_aux(f"History file is not used")

  cnv = Conversation.init()
  current = UserActor(UserName(), ActorOptions.init(), args, header.getvalue())
  st = ActorState.init(current)

  while True:
    response = current.comment_with_text(st.get_view(), cnv)
    assert response.utterance.actor_name == current.name, (
      f"{response.utterance.actor_name} != {current.name}"
    )
    if response.utterance is not None:
      cnv.utterances.append(response.utterance)
    if response.actor_updates is not None:
      for name, opt in response.actor_updates.options.items():
        actor = st.actors.get(name)
        if actor is not None:
          actor.set_options(opt)
        else:
          if name.provider == "openai":
            st.actors[name] = OpenAIActor(name, opt)
          elif name.provider == "gpt4all":
            st.actors[name] = GPT4AllActor(name, opt, args.model_dir)
          elif name.provider == "dummy":
            st.actors[name] = DummyActor(name, opt)
          else:
            raise RuntimeError(f"Unsupported provider {name.provider}")
    if response.actor_next is not None:
      current = st.actors.get(response.actor_next)
    if response.exit_flag:
      break

#     apply(st)
#     repl.reset()
#     try:
#       while all([not repl.exit_request, not repl.reset_request]):
#         repl.visit(PARSER.parse(input(args.readline_prompt)))
#         repl._finish_echo()
#         if args.readline_history:
#           write_history_file(args.readline_history)
#     except (ValueError,RuntimeError) as err:
#       print_aux_err(args, err)
#     except EOFError:
#       print()
#       break

