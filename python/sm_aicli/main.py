import re
from io import StringIO
from os.path import expanduser
from os import chdir
from contextlib import contextmanager
from signal import signal, SIGINT
from sys import _getframe
from pdb import Pdb
from argparse import ArgumentParser

from lark.visitors import Interpreter
from lark import Lark

from sm_aicli import (
  Conversation, ActorState, ActorName, Utterance, UserName, Modality,
  UserActor, ActorOptions, onematch, expanddir, OpenAIActor, GPT4AllActor,
  DummyActor, info, err, with_sigint
)

from .utils import version, REVISION

ARG_PARSER = ArgumentParser(description="Command-line arguments")
ARG_PARSER.add_argument(
  "--model-dir",
  type=str,
  help="Model directory to prepend to model file names"
)
ARG_PARSER.add_argument(
  "--image-dir",
  type=str,
  help="Directory in which to store images"
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
ARG_PARSER.add_argument(
  '-K', '--keep-running',
  action='store_true',
  help="Open interactive shell after processing all positional arguments",
)
ARG_PARSER.add_argument(
  '-C', '--cd',
  type=str,
  help="Change to this directory before execution",
  default=None,
)
ARG_PARSER.add_argument(
  'filenames',
  type=str,
  nargs='*',
  help="List of filenames to process"
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

def get_help_string(arg_parser):
  help_output = StringIO()
  arg_parser.print_help(help_output)
  return help_output.getvalue()

def main(cmdline=None):
  args = ARG_PARSER.parse_args(cmdline)

  if args.cd:
    chdir(args.cd)

  args.help = get_help_string(ARG_PARSER)
  if args.revision or args.version:
    if args.version:
      print(version())
    if args.revision:
      print(REVISION)
    return 0

  cnv = Conversation.init()
  st = ActorState.init()
  current_actor = UserName()
  current_modality = Modality.Text
  user = UserActor(UserName(), ActorOptions.init(), args)
  st.actors[current_actor] = user

  while True:
    try:
      utterance = st.actors[current_actor].react(st.get_view(), cnv)
      assert utterance.actor_name == st.actors[current_actor].name, (
        f"{utterance.actor_name} != {st.actors[current_actor].name}"
      )
      cnv.utterances.append(utterance)
      intention = utterance.intention
      if intention.dbg_flag:
        info("Type `cont` to continue when done", user)
        Pdb(nosigint=True).set_trace(_getframe())
        user._reload_history()
      if intention.actor_updates is not None:
        for name, opt in intention.actor_updates.options.items():
          actor = st.actors.get(name)
          if actor is not None:
            actor.set_options(opt)
          else:
            if name.provider == "openai":
              st.actors[name] = OpenAIActor(name, opt)
            elif name.provider == "gpt4all":
              st.actors[name] = GPT4AllActor(name, opt)
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
      info("^C", user, prefix=False)
      current_actor = UserName()
      current_modality = Modality.Text
    except NotImplementedError as e:
      err("<Not implemented>", user)
      current_actor = UserName()
      current_modality = Modality.Text
    except ValueError as e:
      err(e, user)
      current_actor = UserName()
      current_modality = Modality.Text

