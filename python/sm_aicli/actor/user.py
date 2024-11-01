from lark import Lark
from lark.visitors import Interpreter
from dataclasses import dataclass
from typing import Any

from pdb import set_trace as ST

from ..types import (Actor, ActorName, ActorOptions, ActorRequest, UserName, Utterance,
                     Conversation, ActorView, ModelName, Comment)
from ..grammar import (GRAMMAR, CMD_HELP, CMD_ASK, CMD_EXIT, CMD_ECHO, CMD_MODEL, CMD_NTHREADS,
                       CMD_RESET, CMD_TEMP, CMD_APIKEY, CMD_VERBOSE, CMD_IMG, COMMANDS)

from ..parser import PARSER
from ..utils import print_aux

def as_float(val:str, default:float|None)->float|None:
  return float(val) if val not in {None,"def","default"} else default
def as_int(val:str, default:int|None)->int|None:
  return int(val) if val not in {None,"def","default"} else default


@dataclass
class InterpreterPause(Exception):
  unparsed:int
  request:ActorRequest|None=None
  utterance:Utterance|None=None

class Repl(Interpreter):
  def __init__(self, name, args):
    self._reset()
    self.args = args
    self.av = None
    self.target_actor = None
    self.aname = name
  def _reset(self):
    self.in_echo = 0
    self.message = ""
    self.exit_request = False
  def reset(self):
    old_message = self.message
    self._reset()
    if len(old_message)>0:
      print_aux("Message buffer is now empty")
  def _finish_echo(self):
    if self.in_echo:
      print()
    self.in_echo = 0
  def as_verbatim(self, tree):
    return "verbatim"
  def as_file(self, tree):
    return "file"
  def apikey_value(self, tree):
    return tree.children[0].value
  def apikey_string(self, tree):
    val = self.visit_children(tree)
    return tuple(val) if len(val)==2 else ("verbatim",val[0])
  def mp_gpt4all(self, tree):
    return "gpt4all"
  def mp_openai(self, tree):
    return "openai"
  def mp_dummy(self, tree):
    return "dummy"
  def model_provider(self, tree):
    return tree.children[0].value
  def model_name(self, tree):
    return tree.children[0].value
  def model_string(self, tree):
    val = self.visit_children(tree)
    return tuple(val) if len(val)==2 else ("gpt4all",val[0])
  def command(self, tree):
    self._finish_echo()
    command = tree.children[0].value
    opts = self.av.options
    if command == CMD_ECHO:
      self.in_echo = 1
    elif command in [CMD_ASK, CMD_IMG]:
      raise InterpreterPause(tree.meta.end_pos,
                             utterance=Utterance(self.aname, self.message),
                             request=ActorRequest.init(next_actor=self.target_actor,
                                                       updates=self.av))
    elif command == CMD_HELP:
      print(self.args.help)
      print("Command-line grammar:")
      print(GRAMMAR)
    elif command == CMD_EXIT:
      raise InterpreterPause(tree.meta.end_pos, request=ActorRequest.init(exit_request=True))
    elif command == CMD_MODEL:
      res = self.visit_children(tree)
      if len(res)>2:
        name = ModelName(*res[3])
        opt = opts.get(name, ActorOptions.init())
        print_aux(f"Setting target actor to '{name}'")
        opts[name] = opt
        self.target_actor = name
      else:
        self.target_actor = None
        print_aux(f"Setting target actor to none")
    elif command == CMD_NTHREADS:
      n = as_int(tree.children[2].children[0].value, None)
      opts[self.target_actor].num_threads = n
      print_aux(f"Setting number of threads to '{n or 'default'}'")
    elif command == CMD_TEMP:
      t = as_float(tree.children[2].children[0].value, None)
      opts[self.target_actor].temperature = t
      print_aux(f"Setting model temperature to '{t or 'default'}'")
    elif command == CMD_APIKEY:
      res = self.visit_children(tree)
      if len(res)<3:
        raise ValueError("API key should not be empty")
      schema,arg = res[3]
      opts[self.target_actor].api_key = (schema,arg)
      print_aux(f"Setting API key to \"{schema}:{arg}\"")
    elif command == CMD_VERBOSE:
      v = as_int(tree.children[2].children[0].value, 0)
      opts[self.target_actor].verbose = v
      print_aux(f"Setting actor verbosity to '{v}'")
    elif command == CMD_RESET:
      print_aux("Message buffer will be cleared")
      self.reset()
      # cnv.reset()
      assert False, "TODO"
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
          print_aux(f"Warning: '{cmd}' was parsed as a text")
      self.message += text
  def escape(self, tree):
    text = tree.children[0].value[1:]
    if self.in_echo:
      print(text, end='')
    else:
      self.message += text
  def visit(self, tree, av:ActorView):
    self.av = av
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

  def comment_with_text(self, av:ActorView, cnv:Conversation) -> Comment:
    try:
      while True:
        if self.stream == '':
          self.stream = input(self.args.readline_prompt)
        self.repl.visit(PARSER.parse(self.stream), av)
        self.stream = ''
    except InterpreterPause as p:
      self.stream = self.stream[p.unparsed:]
      return (p.utterance, p.request)


  def set_options(self, mopt:ActorOptions)->None:
    pass

  def get_options(self)->ActorOptions:
    return ActorOptions.init()

