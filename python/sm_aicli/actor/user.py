from gnureadline import write_history_file
from lark import Lark
from lark.visitors import Interpreter
from dataclasses import dataclass
from typing import Any
from copy import deepcopy, copy

from pdb import set_trace as ST

from ..types import (Actor, ActorName, ActorOptions, Intention, UserName, Utterance,
                     Conversation, ActorView, ModelName, Modality)
from ..grammar import (GRAMMAR, CMD_HELP, CMD_ASK, CMD_EXIT, CMD_ECHO, CMD_MODEL, CMD_NTHREADS,
                       CMD_RESET, CMD_TEMP, CMD_APIKEY, CMD_VERBOSE, CMD_IMG, COMMANDS, CMD_PROMPT,
                       CMD_DBG, CMD_EXPECT, CMD_IMGSZ)

from ..utils import info, err, with_sigint, dbg

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
  def _check_next_actor(self):
    if self.actor_next is None:
      raise RuntimeError(no_model_is_active)
  def _reset(self):
    self.in_echo = 0
    self.message = ""
  def reset(self):
    old_message = self.message
    self._reset()
    if len(old_message)>0:
      info("Message buffer is now empty")
  def _finish_echo(self):
    if self.in_echo:
      print()
    self.in_echo = 0
  def as_verbatim(self, tree): return "verbatim"
  def as_file(self, tree): return "file"
  def string_value(self, tree):
    return tree.children[0].value
  def apikey(self, tree):
    val = self.visit_children(tree)
    return tuple(val) if len(val)==2 else ("verbatim",val[0])
  def mp_gpt4all(self, tree):
    return "gpt4all"
  def mp_openai(self, tree):
    return "openai"
  def mp_dummy(self, tree):
    return "dummy"
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
        contents=copy(self.message) if len(self.message.strip())>0 else None
        val = self.visit_children(tree)
        raise InterpreterPause(
          unparsed=tree.meta.end_pos,
          utterance=Utterance.init(
            name=self.aname,
            contents=contents,
            intention=Intention.init(
              actor_next=self.actor_next,
              actor_updates=self.av,
              modality=self.modality
            )
          )
        )
      finally:
        self.message = ''
    elif command == CMD_EXPECT:
      val = self.visit_children(tree)
      modality = val[2][0]
      info(f"Setting expected modality to '{modality}'")
      self.modality = modality
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
        # self.actor_next = None
        # info(f"Setting target actor to none")
    elif command == CMD_NTHREADS:
      n = as_int(tree.children[2].children[0].value, None)
      self._check_next_actor()
      opts[self.actor_next].num_threads = n
      info(f"Setting number of threads to '{n or 'default'}'")
    elif command == CMD_TEMP:
      t = as_float(tree.children[2].children[0].value, None)
      self._check_next_actor()
      opts[self.actor_next].temperature = t
      info(f"Setting model temperature to '{t or 'default'}'")
    elif command == CMD_APIKEY:
      res = self.visit_children(tree)
      if len(res)<2:
        raise ValueError("API key should not be empty")
      schema,arg = res[2][0]
      self._check_next_actor()
      opts[self.actor_next].apikey = (schema,arg)
      info(f"Setting API key to '{schema}:{arg}'")
    elif command == CMD_VERBOSE:
      v = as_int(tree.children[2].children[0].value, 0)
      self._check_next_actor()
      opts[self.actor_next].verbose = v
      info(f"Setting actor verbosity to '{v}'")
    elif command == CMD_PROMPT:
      self._check_next_actor()
      opts[self.actor_next].prompt = self.message
      info(f"Setting actor prompt to '{self.message[:10]}...'")
      self.message = ''
    elif command == CMD_IMGSZ:
      self._check_next_actor()
      v = self.visit_children(tree)[2][0]
      opts[self.actor_next].imgsz = v
      info(f"Setting image size to '{v}'")
    elif command == CMD_RESET:
      info("Message buffer will be cleared")
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
      self.message += text
  def escape(self, tree):
    text = tree.children[0].value[1:]
    if self.in_echo:
      print(text, end='')
    else:
      self.message += text
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
    self.reset()

  def _sync(self, av:ActorView, cnv:Conversation):
    assert self.cnv_top <= len(cnv.utterances)
    if self.repl.av is None:
      self.repl.av = av
    for i in range(self.cnv_top, len(cnv.utterances)):
      u:Utterance = cnv.utterances[i]
      if u.actor_name != self.name:
        need_eol = False
        if u.contents is not None:
          need_eol = not u.contents.rstrip(' ').endswith("\n")
          print(u.contents, end='')
        elif u.gen is not None:
          def _handler(*args, **kwargs):
            u.interrupt()
          with with_sigint(_handler):
            for token in u.gen(u):
              need_eol = not token.rstrip(' ').endswith("\n")
              print(token, end='', flush=True)
        if u.resources is not None:
          for r in u.resources:
            if r.modality == Modality.Image:
              print(f"/img \"{r.path}\"\n", end='', flush=True)
            else:
              assert False, f"Unexpected resource modality {r.modality}"
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
            self.stream = input(self.args.readline_prompt)
          self.repl.visit(PARSER.parse(self.stream))
          if self.args.readline_history:
            write_history_file(self.args.readline_history)
        except (ValueError, RuntimeError) as e:
          err(str(e), actor=self)
        self.stream = ''
    except InterpreterPause as p:
      self.stream = self.stream[p.unparsed:]
      return p.utterance
    except EOFError:
      self.stream = ''
      return Utterance.init(
        name=self.name,
        intention=Intention.init(exit_flag=True)
      )

  def set_options(self, opt:ActorOptions)->None:
    pass

  def get_options(self)->ActorOptions:
    return ActorOptions.init()

