from lark import Lark
from lark.visitors import Interpreter
from dataclasses import dataclass

from ..types import Actor, ActorName, ActorOptions, ActorRequest, UserName, Utterance, Conversation
from ..grammar import GRAMMAR
from ..parser import PARSER

@dataclass
class InterpreterPause(Exception):
  unparsed:int
  request:ActorRequest|None
  utterance:Utterance|None

class Repl(Interpreter):
  def __init__(self):
    self._reset()
    self.ust = UserInputState.init()
  def _reset(self):
    self.in_echo = False
    self.message = ""
    self.exit_request = False
  def reset(self):
    old_message = self.message
    self._reset()
    if len(old_message)>0:
      print_aux(args, "Message buffer is now empty")
  def _finish_echo(self):
    if self.in_echo:
      print()
    self.in_echo = False
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
    if self.exit_request:
      raise RuntimeError("No commands are allowed after /exit")
    self._finish_echo()
    command = tree.children[0].value
    ust = self.ust
    mopt = ust.options.get(ust.current_model_name)
    if command == CMD_ECHO:
      self.in_echo = True
    elif command in [CMD_ASK, CMD_IMG]:
      if command == CMD_ASK:
        ask_text(args, st, cnv)
      elif command == CMD_IMG:
        ask_img(args, st, cnv)
      else:
        assert False
    elif command == CMD_HELP:
      print_help()
    elif command == CMD_EXIT:
      self.exit_request = True
    elif command == CMD_MODEL:
      res = self.visit_children(tree)
      if len(res)>2:
        mname = ModelName(*res[3])
        mopt = st.options.get(mname, ModelOptions.init())
        print_aux(args, f"Setting current model to '{mname}'")
        st.current_model_name = mname
      else:
        st.current_model_name = None
        print_aux(args, f"Setting current model to none")
    elif command == CMD_NTHREADS:
      n = as_int(tree.children[2].children[0].value, None)
      st.options[st.current_model_name].num_threads = n
      print_aux(args, f"Setting number of threads to '{n or 'default'}'")
    elif command == CMD_TEMP:
      t = as_float(tree.children[2].children[0].value, None)
      st.options[st.current_model_name].temperature = t
      print_aux(args, f"Setting model temperature to '{t or 'default'}'")
    elif command == CMD_RESET:
      print_aux(args, "Message buffer will be cleared")
      self.reset()
      cnv.reset()
    elif command == CMD_APIKEY:
      res = self.visit_children(tree)
      if len(res)<3:
        raise ValueError("API key should not be empty")
      schema,arg = res[3]
      st.options[st.current_model_name].api_key = (schema,arg)
      print_aux(args, f"Setting API key to \"{schema}:{arg}\"")
    elif command == CMD_VERBOSE:
      v = as_int(tree.children[2].children[0].value, 0)
      st.options[st.current_model_name].verbose = v
      print_aux(args, f"Setting model verbosity to '{v}'")
    else:
      raise ValueError(f"Unknown command: {command}")
  def text(self, tree):
    text = tree.children[0].value
    if self.in_echo:
      print(text, end='')
    else:
      for cmd in COMMANDS:
        if cmd in text:
          print_aux(args, f"Warning: '{cmd}' was parsed as a text")
      self.message += text
  def escape(self, tree):
    text = tree.children[0].value[1:]
    if self.in_echo:
      print(text, end='')
    else:
      self.message += text



class UserActor(Actor):

  def __init__(self,
               name:ActorName,
               opt:ActorOptions,
               readline_prompt:str,
               prefix_stream:str|None=None):
    super().__init__(name, opt)
    self.stream = prefix_stream if prefix_stream is not None else ''
    self.readline_prompt = readline_prompt
    self.repl = Repl()

  def comment_with_text(self, cnv:Conversation) -> tuple[Utterance|None, ActorRequest|None]:
    try:
      while True:
        if self.stream == '':
          self.stream = input(self.readline_prompt)
        self.repl.visit(PARSER.parse(self.stream))
        self.stream = ''
    except InterpreterPause as p:
      del self.stream[:p.unparsed]
      return p.utterance, p.request


  def set_options(self, mopt:ActorOptions)->None:
    pass

  def get_options(self)->ActorOptions:
    return ActorOptions.init()

