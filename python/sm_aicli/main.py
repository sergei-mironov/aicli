import re
from io import StringIO
from os.path import expanduser, abspath
from os import chdir, environ, getcwd
from contextlib import contextmanager
from signal import signal, SIGINT
from sys import _getframe
from pdb import Pdb
from argparse import ArgumentParser
from typing import Any
from functools import partial
from gnureadline import (parse_and_bind, clear_history, read_history_file,
                         write_history_file, set_completer, set_completer_delims)

from lark.visitors import Interpreter
from lark import Lark

from sm_aicli import (
  Conversation, ActorState, ActorName, Utterance, UserName, Modality,
  UserActor, ActorOptions, onematch, expanddir, OpenAIActor, GPT4AllActor,
  DummyActor, info, err, with_sigint, args2script, File, Parser, read_configs
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
ARG_PARSER.add_argument(
  '--readline-history',
  type=str,
  metavar='FILE',
  help=f"History file name, disabled by default.",
  default=None
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


class StdinFile(File):
  def __init__(self, args:Any, stream):
    self.args = args
    self.stream = stream
    self.batch_mode = len(args.filenames) > 0

    if args.readline_history is None:
      args.readline_history = environ.get("AICLI_HISTORY")
    if args.readline_history is not None:
      args.readline_history = abspath(expanduser(args.readline_history))
    self._reload_history()

  def _reload_history(self):
    if self.args.readline_history is not None:
      try:
        clear_history()
        read_history_file(self.args.readline_history)
        info(f"History file loaded")
      except FileNotFoundError:
        info(f"History file not loaded")
    else:
      info(f"History file is not used")

  def would_block(self)->bool:
    return len(self.stream.strip())==0

  def process(self, parser:Parser, prompt:str) -> tuple[bool, Any]:
    try:
      if len(self.stream) == 0:
        if self.batch_mode and not self.args.keep_running:
          return True, None
        self.stream = input(prompt) + '\n'
        if self.args.readline_history is not None:
          write_history_file(self.args.readline_history)
      self.stream, res = parser.parse(self.stream)
      return False, res
    except EOFError:
      return True, None


def main(cmdline=None, providers=None):
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

  if args.readline_history is None:
    args.readline_history = environ.get("AICLI_HISTORY")
  if args.readline_history is not None:
    args.readline_history = abspath(expanduser(args.readline_history))

  rcnames = environ.get('AICLI_RC', args.rc)
  if rcnames is not None and len(rcnames)>0 and rcnames!='none':
    configs = read_configs(rcnames.split(','))
  else:
    info("Skipping configuration files")
    configs = []

  file = StdinFile(args, args2script(args, configs))

  providers = {
    "openai": OpenAIActor,
    "gpt4all": GPT4AllActor,
    "dummy": partial(DummyActor, file=file),
  } if providers is None else providers

  cnv = Conversation.init()
  st = ActorState.init()
  current_actor = UserName()
  current_modality = Modality.Text
  user = UserActor(UserName(), ActorOptions.init(), args, file)
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
        user.logger.info("Type `cont` to continue when done")
        Pdb(nosigint=True).set_trace(_getframe())
        file._reload_history()
      if intention.actor_updates is not None:
        for name, opt in intention.actor_updates.options.items():
          actor = st.actors.get(name)
          if actor is not None:
            actor.set_options(opt)
          else:
            provider = providers.get(name.provider)
            if provider is None:
              raise RuntimeError(f"Unsupported provider {name.provider}")
            st.actors[name] = provider(name, opt)
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

