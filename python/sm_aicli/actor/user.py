from gnureadline import write_history_file
from lark import Lark
from lark.visitors import Interpreter
from dataclasses import dataclass
from typing import Any
from copy import deepcopy, copy
from sys import stdout

from pdb import set_trace as ST

from ..types import (Actor, ActorName, ActorOptions, Intention, UserName, Utterance,
                     Conversation, ActorView, ModelName, Modality, Stream)

from ..utils import info, err, with_sigint, dbg, cont2strm, VERSION, REVISION

CMD_HELP = "/help"
CMD_ASK  = "/ask"
CMD_EXIT = "/exit"
CMD_ECHO = "/echo"
CMD_MODEL = "/model"
CMD_RESET = "/reset"
CMD_CLEAR = "/clear"
CMD_DBG = "/dbg"
CMD_VERSION = "/version"
CMD_LOAD = "/load"
CMD_LOADBIN = "/loadbin"
CMD_SET = "/set"
CMD_READ = "/read"
CMD_COPY = "/copy"

COMMANDS = [CMD_HELP, CMD_EXIT, CMD_ECHO, CMD_MODEL, CMD_RESET, CMD_LOADBIN, CMD_DBG,
            CMD_ASK, CMD_VERSION, CMD_LOAD, CMD_CLEAR, CMD_SET, CMD_COPY]
COMMANDS_ARG = [CMD_MODEL, CMD_LOADBIN, CMD_LOAD, CMD_SET, CMD_READ, CMD_COPY]
COMMANDS_NOARG = r'|'.join(sorted(list(set(COMMANDS)-set(COMMANDS_ARG)))).replace('/','\\/')

GRAMMAR = fr"""
  start: (command | escape | text)? (command | escape | text)*
  escape.3: /\\./
  command.2: /{COMMANDS_NOARG}/ | \
             /\/model/ / +/ model_string | \
             /\/img/ / +/ string | \
             /\/load/ / +/ filename | \
             /\/loadbin/ / +/ filename | \
             /\/read/ / +/ /model/ / +/ /prompt/ | \
             /\/set/ / +/ (/model/ / +/ (/apikey/ / +/ apikey_string | \
                                         (/t/ | /temp/) / +/ (float | def) | \
                                         (/nt/ | /nthreads/) / +/ (number | def) | \
                                         /imgsz/ / +/ string | \
                                         /verbosity/ / +/ (number | def)) | \
                           (/term/ | /terminal/) / +/ (/modality/ / +/ modality_string | \
                                                       /rawbin/ / +/ bool)) | \
             /\/copy/ / +/ apikey_string / +/ apikey_string

  string: "\"" string_quoted "\"" | string_raw
  string_quoted: /[^"]+/ -> string_value
  string_raw: /[^"][^ ]*/ -> string_value

  model_string: "\"" model_quoted "\"" | model_raw
  model_quoted: (model_provider ":")? string_quoted -> model
  model_raw: (model_provider ":")? string_raw -> model
  model_provider: "gpt4all" -> mp_gpt4all | "openai" -> mp_openai | "dummy" -> mp_dummy

  modality_string: "\"" modality "\"" | modality
  modality: /img/ -> modality_img | /text/ -> modality_text

  apikey_string: "\"" apikey_quoted "\"" | apikey_raw
  apikey_quoted: (apikey_schema ":")? string_quoted -> apikey
  apikey_raw: (apikey_schema ":")? string_raw -> apikey
  apikey_schema: /verbatim/ | /file/ | /buf/ -> apikey_schema

  filename: string
  number: /[0-9]+/
  float: /[0-9]+\.[0-9]*/
  def: "default"
  bool: /true/|/false/|/yes/|/no/|/1/|/0/
  text.0: /(.(?!\/|\\))*./s
"""

PARSER = Lark(GRAMMAR, start='start', propagate_positions=True)

no_model_is_active = "No model is active, use /model first"

def as_float(val:str, default:float|None)->float|None:
  return float(val) if val not in {None,"def","default"} else default
def as_int(val:str, default:int|None)->int|None:
  return int(val) if val not in {None,"def","default"} else default


@dataclass
class InterpreterPause(Exception):
  unparsed:int
  utterance:Utterance

class Repl(Interpreter):
  def __init__(self, name, args):
    self._reset()
    self.args = args
    self.av = None
    self.actor_next = None
    self.aname = name
    self.modality = Modality.Text
    self.rawbin = False
  def _check_next_actor(self):
    if self.actor_next is None:
      raise RuntimeError(no_model_is_active)
  def _reset(self):
    self.in_echo = 0
    self.buffer_main = ""
    self.buffer_result = ""
  def reset(self):
    old_message = self.buffer_main
    self._reset()
    if len(old_message)>0:
      info("Message buffer is now empty")
  def _finish_echo(self):
    if self.in_echo:
      print()
    self.in_echo = 0
  def string_value(self, tree):
    return tree.children[0].value
  def apikey_schema(self, tree):
    return str(tree.children[0])
  def apikey(self, tree):
    val = self.visit_children(tree)
    return tuple(val) if len(val)==2 else ("verbatim",val[0])
  def mp_gpt4all(self, tree):
    return "gpt4all"
  def mp_openai(self, tree):
    return "openai"
  def mp_dummy(self, tree):
    return "dummy"
  def bool(self, tree):
    val = self.visit_children(tree)[0]
    if val in ['true','yes','1']:
      return [True]
    elif val in ['false','no','0']:
      return [False]
    else:
      raise ValueError(f"Invalid boolean value {val}")
  def model(self, tree):
    val = self.visit_children(tree)
    return tuple(val) if len(val)==2 else (val[0],"default")
  def modality_img(self, tree): return Modality.Image
  def modality_text(self, tree): return Modality.Text
  def command(self, tree):
    self._finish_echo()
    command = tree.children[0].value
    opts = self.av.options
    if command == CMD_ECHO:
      self.in_echo = 1
    elif command == CMD_ASK:
      try:
        contents=copy(self.buffer_main) if len(self.buffer_main.strip())>0 else None
        val = self.visit_children(tree)
        raise InterpreterPause(
          unparsed=tree.meta.end_pos,
          utterance=Utterance.init(
            name=self.aname,
            contents=[contents],
            intention=Intention.init(
              actor_next=self.actor_next,
              actor_updates=self.av,
              modality=self.modality
            )
          )
        )
      finally:
        self.buffer_main = ''
    elif command == CMD_HELP:
      print(self.args.help)
      print("Command-line grammar:")
      print(GRAMMAR)
    elif command == CMD_EXIT:
      raise InterpreterPause(
        unparsed=tree.meta.end_pos,
        utterance=Utterance.init(
          name=self.aname,
          intention=Intention.init(exit_flag=True, actor_updates=self.av)
        )
      )
    elif command == CMD_MODEL:
      res = self.visit_children(tree)
      if len(res)>2:
        name = ModelName(*res[2][0])
        opt = opts.get(name, ActorOptions.init())
        info(f"Setting target actor to '{name.repr()}'")
        opts[name] = opt
        self.actor_next = name
      else:
        raise ValueError("Invalid model format")
    elif command == CMD_SET:
      args = self.visit_children(tree)
      section, pname, pval = args[2], args[4], args[6][0]
      if section == 'model':
        self._check_next_actor()
        if pname == 'apikey':
          if not isinstance(pval, tuple) or len(pval)!=2:
            raise ValueError("Model API key should be formatted as `schema:value`")
          opts[self.actor_next].apikey = pval
          info(f"Setting model API key to '{pval[0]}:{pval[1]}'")
        elif pname in ['t','temp']:
          opts[self.actor_next].temperature = pval
          info(f"Setting model temperature to '{pval or 'default'}'")
        elif pname in ['nt','nthreads']:
          opts[self.actor_next].num_threads = pval
          info(f"Setting model number of threads to '{pval or 'default'}'")
        elif pname == 'imgsz':
          opts[self.actor_next].imgsz = pval
          info(f"Setting model image size to '{pval}'")
        elif pname == 'verbosity':
          opts[self.actor_next].verbose = pval
          info(f"Setting actor verbosity to '{pval}'")
        else:
          raise ValueError(f"Unknown actor parameter '{pname}'")
      elif section in ['term','terminal']:
        if pname == 'modality':
          info(f"Setting terminal expected modality to '{pval}'")
          self.modality = pval
        elif pname == 'rawbin':
          info(f"Setting terminal raw binary mode to '{pval}'")
          self.rawbin = pval
        else:
          raise ValueError(f"Unknown terminal parameter '{pname}'")
      else:
        raise ValueError(f"Unknown set section '{section}'")
    elif command == CMD_READ:
      args = self.visit_children(tree)
      section, pname, pval = args[2], args[4], self.buffer_main.strip()
      assert section == 'model'
      self._check_next_actor()
      if pname == 'prompt':
        opts[self.actor_next].prompt = pval
        info(f"Setting actor prompt to '{pval[:10]}...'")
      else:
        raise ValueError(f"Unknown read parameter '{pname}'")
      self.buffer_main = ''
    elif command == CMD_LOAD:
      fname = self.visit_children(tree)[2][0][0]
      info(f"Loading text file '{fname}' into buffer")
      with open(fname) as f:
        self.buffer_main += f.read()
    elif command == CMD_LOADBIN:
      fname = self.visit_children(tree)[2][0][0]
      info(f"Loading binary file '{fname}' into buffer")
      acc = b''
      with open(fname, 'rb') as f:
        acc += f.read()
      self.buffer_main = acc
    elif command == CMD_CLEAR:
      info("Clearing message buffer")
      self.reset()
    elif command == CMD_RESET:
      info("Resetting conversation history and clearing message buffer")
      self.reset()
      raise InterpreterPause(
        unparsed=tree.meta.end_pos,
        utterance=Utterance.init(
          name=self.aname,
          intention=Intention.init(reset_flag=True)
        )
      )
    elif command == CMD_DBG:
      info("Calling Python debugger")
      raise InterpreterPause(
        unparsed=tree.meta.end_pos,
        utterance=Utterance.init(
          name=self.aname,
          intention=Intention.init(dbg_flag=True)
        )
      )
    elif command == CMD_COPY:
      ST()
      pass
    elif command == CMD_VERSION:
      print(f"{VERSION}+g{REVISION[:7]}")
    else:
      raise ValueError(f"Unknown command: {command}")
  def text(self, tree):
    text = tree.children[0].value
    if self.in_echo:
      if self.in_echo == 1:
        print(text.lstrip(), end='')
        self.in_echo = 2
      else:
        print(text, end='')
    else:
      for cmd in COMMANDS:
        if cmd in text:
          info(f"Warning: '{cmd}' was parsed as a text")
      self.buffer_main += text
  def escape(self, tree):
    text = tree.children[0].value[1:]
    if self.in_echo:
      print(text, end='')
    else:
      self.buffer_main += text
  def visit(self, tree):
    self.in_echo = 0
    try:
      res = super().visit(tree)
    finally:
      self._finish_echo()
    return res




class UserActor(Actor):

  def __init__(self,
               name:ActorName,
               opt:ActorOptions,
               args:Any,
               prefix_stream:str|None=None):
    super().__init__(name, opt)
    self.stream = prefix_stream if prefix_stream is not None else ''
    self.args = args
    self.repl = Repl(name, args)
    self.batch_mode = len(args.filenames)>0
    self.reset()

  def _sync(self, av:ActorView, cnv:Conversation):
    assert self.cnv_top <= len(cnv.utterances)
    if self.repl.av is None:
      self.repl.av = av
    for i in range(self.cnv_top, len(cnv.utterances)):
      u:Utterance = cnv.utterances[i]
      if u.actor_name != self.name:
        need_eol = False
        for cont in u.contents:
          s = cont2strm(cont)
          def _handler(*args, **kwargs):
            s.interrupt()
          with with_sigint(_handler):
            if s.binary and not self.repl.rawbin:
              assert s.suggested_fname is not None, \
                f"Suggested file name for binary stream must be set"
              with open(s.suggested_fname, 'wb') as f:
                for token in s.gen():
                  f.write(token)
              info(f"Binary file has been saved to '{s.suggested_fname}'")
              cmd = f"/loadbin \"{s.suggested_fname}\""
              print(cmd, flush=True)
              self.stream = cmd + self.stream
            else:
              for token in s.gen():
                if isinstance(token, bytes):
                  need_eol = True
                  stdout.buffer.write(token)
                  stdout.buffer.flush()
                elif isinstance(token, str):
                  need_eol = not token.rstrip(' ').endswith("\n")
                  print(token, end='', flush=True)
        if need_eol:
          print()
      self.cnv_top += 1

  def reset(self):
    self.cnv_top = 0

  def react(self, av:ActorView, cnv:Conversation) -> Utterance:
    self._sync(av, cnv)
    try:
      while True:
        try:
          if self.stream == '':
            if self.batch_mode:
              break
            else:
              self.stream = input(self.args.readline_prompt)
          self.repl.visit(PARSER.parse(self.stream))
          if self.args.readline_history:
            write_history_file(self.args.readline_history)
        except (ValueError, RuntimeError, FileNotFoundError) as e:
          err(str(e), actor=self)
        self.stream = ''
    except InterpreterPause as p:
      self.stream = self.stream[p.unparsed:]
      return p.utterance
    except EOFError:
      print()
    return Utterance.init(
      name=self.name,
      intention=Intention.init(exit_flag=True)
    )

  def set_options(self, opt:ActorOptions)->None:
    pass

  def get_options(self)->ActorOptions:
    return ActorOptions.init()

