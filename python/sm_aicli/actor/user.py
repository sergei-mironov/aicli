from gnureadline import write_history_file
from lark import Lark, Token
from lark.exceptions import LarkError
from lark.visitors import Interpreter
from dataclasses import dataclass
from typing import Any
from copy import deepcopy, copy
from sys import stdout, stderr
from collections import defaultdict
from os import system, chdir
from os.path import expanduser

from pdb import set_trace as ST

from ..types import (Actor, ActorName, ActorOptions, Intention, UserName, Utterance,
                     Conversation, ActorView, ModelName, Modality, Stream)

from ..utils import info, err, with_sigint, dbg, cont2strm, VERSION, REVISION, sys2exitcode

CMD_APPEND = "/append"
CMD_ASK  = "/ask"
CMD_CAT = "/cat"
CMD_CLEAR = "/clear"
CMD_CP = "/cp"
CMD_DBG = "/dbg"
CMD_ECHO = "/echo"
CMD_EXIT = "/exit"
CMD_HELP = "/help"
CMD_MODEL = "/model"
CMD_READ = "/read"
CMD_RESET = "/reset"
CMD_SET = "/set"
CMD_SHELL = "/shell"
CMD_VERSION = "/version"
CMD_CD = "/cd"
CMD_PASTE = "/paste"

SCHEMAS = ["buf", "buffer", "file", "bfile", "verbatim"]
PROVIDERS = ["openai", "gpt4all", "dummy"]

GRAMMAR = fr"""
  start: (command | escape | text)? (command | escape | text)*
  text: TEXT
  escape: ESCAPE
  # Commands start with `/`. Use `\/` to process next `/` as a regular text.
  # The commands are:
  # {CMD_APPEND} TYPE:FROM TYPE:TO - Append a file, a buffer or a constant to a file or to a buffer.
  # {CMD_CAT} TYPE:WHAT            - Print a file or buffer to STDOUT.
  # {CMD_CP} TYPE:FROM TYPE:TO     - Copy a file, a buffer or a constant into a file or into a buffer.
  # {CMD_MODEL} PROVIDER:NAME      - Set the current model to `model_string`. Allocate the model on first use.
  # {CMD_READ} WHERE               - Reads the content of the 'IN' buffer into a special variable.
  # {CMD_SET} WHAT                 - Set terminal or model option
  # {CMD_SHELL} TYPE:FROM          - Run a shell command.
  # {CMD_CLEAR}                    - Clear the buffer named `ref_string`.
  # {CMD_RESET}                    - Reset the conversation and all the models
  # {CMD_VERSION}                  - Print version
  # {CMD_DBG}                      - Run the Python debugger
  # {CMD_ECHO}                     - Echo the following line to STDOUT
  # {CMD_EXIT}                     - Exit
  # {CMD_HELP}                     - Print help
  # {CMD_CD} REF                   - Change the current directory to the specified path
  # {CMD_PASTE} BOOL               - Enable or disable paste mode
  command: /\{CMD_VERSION}/ | \
           /\{CMD_DBG}/ | \
           /\{CMD_RESET}/ | \
           /\{CMD_ECHO}/ | \
           /\{CMD_ASK}/ | \
           /\{CMD_HELP}/ | \
           /\{CMD_EXIT}/ | \
           /\{CMD_MODEL}/ / +/ model_ref | \
           /\{CMD_READ}/ / +/ /model/ / +/ /prompt/ | \
           /\{CMD_SET}/ / +/ (/model/ / +/ (/apikey/ / +/ ref | \
                                       (/t/ | /temp/) / +/ (FLOAT | DEF) | \
                                       (/nt/ | /nthreads/) / +/ (NUMBER | DEF) | \
                                       /imgsz/ / +/ string | \
                                       /verbosity/ / +/ (NUMBER | DEF)) | \
                             (/term/ | /terminal/) / +/ (/modality/ / +/ modality_string | \
                                                         /rawbin/ / +/ BOOL)) | \
           /\{CMD_CP}/ / +/ ref / +/ ref | \
           /\{CMD_APPEND}/ / +/ ref / +/ ref | \
           /\{CMD_CAT}/ / +/ ref | \
           /\{CMD_CLEAR}/ / +/ ref | \
           /\{CMD_SHELL}/ / +/ ref | \
           /\{CMD_CD}/ / +/ ref | \
           /\{CMD_PASTE}/ / +/ BOOL

  # Strings can start and end with a double-quote. Unquoted strings should not contain spaces.
  string: "\"" string_quoted "\"" | string_unquoted
  string_quoted: STRING_QUOTED -> string_value
  string_unquoted: STRING_UNQUOTED -> string_value

  model_ref: (PROVIDER ":")? string

  # Modalities are either `img` or `text`.
  modality_string: "\"" modality "\"" | modality
  modality: /img/ -> modality_img | /text/ -> modality_text

  # References mention locations which could be either a file (`file:path/to/file`), a binary file
  # (`bfile:path/to/file`), a named memory buffer (`buffer:name`) or a read-only string constant
  # (`verbatim:ABC`).
  ref: (SCHEMA ":")? string -> ref | \
       /file/ (/\(/ | /\(/ / +/) ref (/\)/ | / +/ /\)/) -> ref_file

  # Base token types
  ESCAPE.5: /\\./
  SCHEMA.4: {'|'.join([f"/{s}/" for s in SCHEMAS])}
  PROVIDER.4: {'|'.join([f"/{p}/" for p in PROVIDERS])}
  STRING_QUOTED.3: /[^"]+/
  STRING_UNQUOTED.3: /[^"\(\)][^ \(\)\n]*/
  TEXT.0: /([^\/#](?!\/|\\))*[^\/#]/s
  NUMBER: /[0-9]+/
  FLOAT: /[0-9]+\.[0-9]*/
  DEF: "default"
  BOOL: /true/|/false/|/yes/|/no/|/1/|/0/
  %ignore /#[^\n]*/
"""

PARSER = Lark(GRAMMAR, start='start', propagate_positions=True)

no_model_is_active = "No model is active, use /model first"

def as_float(val:Token, default:float|None=None)->float|None:
  assert val.type == 'FLOAT', val
  return float(val) if str(val) not in {"def","default"} else default

def as_int(val:Token, default:int|None=None)->int|None:
  assert val.type == 'NUMBER', val
  return int(val) if str(val) not in {"def","default"} else default

def as_bool(val:Token):
  assert val.type == 'BOOL', val
  if str(val) in ['true','yes','1']:
    return True
  elif str(val) in ['false','no','0']:
    return False
  else:
    raise ValueError(f"Invalid boolean value {val}")

def ref_write(ref, val:str|bytes, buffers, append:bool=False):
  schema, name = ref
  a = "a" if append else ""
  if schema in 'file':
    try:
      with open(name, f"w{a}") as f:
        f.write(val.encode('utf-8') if isinstance(val, bytes) else val)
    except Exception as err:
      raise ValueError(str(err)) from err
  elif schema in 'bfile':
    try:
      with open(name, f"bw{a}") as f:
        f.write(val.decode() if isinstance(val, str) else val)
    except Exception as err:
      raise ValueError(str(err)) from err
  elif schema == 'buffer':
    if append:
      buffers[name.lower()] += val
    else:
      buffers[name.lower()] = val
  else:
    raise ValueError(f"Unsupported target schema '{schema}'")

def ref_read(ref, buffers)->str|None:
  schema, name = ref
  if schema=="verbatim":
    return name
  elif schema in ["file", "bfile"]:
    try:
      mode = "rb" if schema == "bfile" else "r"
      with open(expanduser(name), mode) as f:
        return f.read().strip()
    except Exception as err:
      raise ValueError(str(err)) from err
  elif schema == 'buffer':
    return buffers[name.lower()]
  else:
    raise ValueError(f"Unsupported reference schema '{schema}'")

@dataclass
class InterpreterPause(Exception):
  unparsed:int
  utterance:Utterance

IN='in'
OUT='out'

class Repl(Interpreter):
  def __init__(self, name, args):
    self.buffers = defaultdict(str)
    self.args = args
    self.av = None
    self.actor_next = None
    self.aname = name
    self.modality = Modality.Text
    self.rawbin = False
    self.ref_schema_default = "verbatim"
    self._reset()
    self.paste_mode = False

  def _check_next_actor(self):
    if self.actor_next is None:
      raise RuntimeError(no_model_is_active)

  def _reset(self):
    self.in_echo = 0
    self.buffers[IN] = ""
    self.buffers[OUT] = ""

  def reset(self):
    old_message = self.buffers[IN]
    self._reset()
    if len(old_message) > 0:
      info("Message buffer is now empty")

  def _finish_echo(self):
    if self.in_echo:
      print()
    self.in_echo = 0

  def string_value(self, tree):
    return tree.children[0].value

  def ref(self, tree):
    val = self.visit_children(tree)
    return (str(val[0]), val[1][0]) if len(val) == 2 else (self.ref_schema_default, val[0][0])

  def ref_file(self, tree):
    args = self.visit_children(tree)
    val = ref_read(args[2], self.buffers)
    return ("file", val.strip())

  def mp_gpt4all(self, tree):
    return "gpt4all"

  def mp_openai(self, tree):
    return "openai"

  def mp_dummy(self, tree):
    return "dummy"

  def bool(self, tree):
    val = self.visit_children(tree)[0]
    if val in ['true', 'yes', '1']:
      return [True]
    elif val in ['false', 'no', '0']:
      return [False]
    else:
      raise ValueError(f"Invalid boolean value {val}")

  def model_ref(self, tree):
    val = self.visit_children(tree)
    return (str(val[0]), val[1][0]) if len(val) == 2 else (val[0][0], "default")

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
        contents = [copy(self.buffers[IN])] if len(self.buffers[IN].strip()) > 0 else []
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
        self.buffers[IN] = ''
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
      if len(res) > 2:
        name = ModelName(*res[2])
        opt = opts.get(name, ActorOptions.init())
        info(f"Setting target actor to '{name.repr()}'")
        opts[name] = opt
        self.actor_next = name
      else:
        raise ValueError("Invalid model format")
    elif command == CMD_SET:
      self.ref_schema_default = "verbatim"
      args = self.visit_children(tree)
      section, pname, pval = args[2], args[4], args[6]
      if section == 'model':
        self._check_next_actor()
        if pname == 'apikey':
          if not isinstance(pval, tuple) or len(pval) != 2:
            raise ValueError("Model API key should be formatted as `schema:value`")
          opts[self.actor_next].apikey = ref_read(pval, self.buffers)
          info(f"Setting model API key to the contents of '{pval[0]}:{pval[1]}'")
        elif pname in ['t', 'temp']:
          val = as_float(pval)
          opts[self.actor_next].temperature = val
          info(f"Setting model temperature to '{val or 'default'}'")
        elif pname in ['nt', 'nthreads']:
          val = as_int(pval)
          opts[self.actor_next].num_threads = val
          info(f"Setting model number of threads to '{val or 'default'}'")
        elif pname == 'imgsz':
          opts[self.actor_next].imgsz = pval
          info(f"Setting model image size to '{pval}'")
        elif pname == 'verbosity':
          val = as_int(pval)
          opts[self.actor_next].verbose = val
          info(f"Setting actor verbosity to '{val}'")
        else:
          raise ValueError(f"Unknown actor parameter '{pname}'")
      elif section in ['term', 'terminal']:
        if pname == 'modality':
          info(f"Setting terminal expected modality to '{pval}'")
          self.modality = pval
        elif pname == 'rawbin':
          val = as_bool(pval)
          info(f"Setting terminal raw binary mode to '{val}'")
          self.rawbin = val
        else:
          raise ValueError(f"Unknown terminal parameter '{pname}'")
      else:
        raise ValueError(f"Unknown set section '{section}'")
    elif command == CMD_READ:
      args = self.visit_children(tree)
      section, pname, pval = args[2], args[4], self.buffers[IN].strip()
      assert section == 'model'
      self._check_next_actor()
      if pname == 'prompt':
        opts[self.actor_next].prompt = pval
        info(f"Setting actor prompt to '{pval[:10]}...'")
      else:
        raise ValueError(f"Unknown read parameter '{pname}'")
      self.buffers[IN] = ''
    elif command == CMD_CLEAR:
      self.ref_schema_default = "buffer"
      args = self.visit_children(tree)
      (schema, name) = args[2]
      if schema != 'buffer':
        raise ValueError(f'Required reference to buffer, not {schema}')
      info(f"Clearing buffer \"{name.lower()}\"")
      ref_write((schema, name), '', self.buffers, append=False)
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
    elif command in [CMD_CP, CMD_APPEND]:
      append = (command == CMD_APPEND)
      self.ref_schema_default = "buffer"
      args = self.visit_children(tree)
      sref, dref = args[2], args[4]
      val = ref_read(sref, self.buffers)
      ref_write(dref, val, self.buffers, append=append)
      info(f"{'Appended' if append else 'Copied'} from {sref} to {dref}")
    elif command == CMD_CAT:
      self.ref_schema_default = "buffer"
      args = self.visit_children(tree)
      ref = args[2]
      val = ref_read(ref, self.buffers)
      print(val)
    elif command == CMD_SHELL:
      self.ref_schema_default = "verbatim"
      args = self.visit_children(tree)
      ref = args[2]
      val = ref_read(ref, self.buffers)
      retcode = sys2exitcode(system(val))
      info(f"Shell command '{val}' exited with code {retcode}")
    elif command == CMD_CD:
      self.ref_schema_default = "verbatim"
      args = self.visit_children(tree)
      ref = args[2]
      path = ref_read(ref, self.buffers)
      try:
        chdir(path)
        info(f"Changed current directory to '{path}'")
      except Exception as err:
        raise ValueError(str(err)) from err
    elif command == CMD_VERSION:
      print(f"{VERSION}+g{REVISION[:7]}")
    elif command == CMD_PASTE:
      args = self.visit_children(tree)
      paste_state = as_bool(args[2])
      if paste_state:
        info("Entering paste mode. Type '/paste off' to finish.")
        self.paste_mode = True
      else:
        info("Exiting paste mode.")
        self.paste_mode = False
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
      self.buffers[IN] += text

  def escape(self, tree):
    text = tree.children[0].value[1:]
    if self.in_echo:
      print(text, end='')
    else:
      self.buffers[IN] += text

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
               prefix_stream:str|None = None):
    super().__init__(name, opt)
    self.stream = prefix_stream if prefix_stream is not None else ''
    self.args = args
    self.repl = Repl(name, args)
    self.batch_mode = len(args.filenames) > 0
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
              cmd = f"{CMD_CP} \"bfile:{s.suggested_fname}\" \"buffer:out\""
              print(cmd, flush=True)
              self.stream = cmd + self.stream
            else:
              self.repl.buffers[OUT] = None
              for token in s.gen():
                if isinstance(token, bytes):
                  need_eol = True
                  stdout.buffer.write(token)
                  stdout.buffer.flush()
                elif isinstance(token, str):
                  need_eol = not token.rstrip(' ').endswith("\n")
                  print(token, end='', flush=True)
                if self.repl.buffers[OUT] is None:
                  self.repl.buffers[OUT] = b'' if isinstance(token, bytes) else ''
                self.repl.buffers[OUT] += token
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
            if self.batch_mode and not self.args.keep_running:
              break
            else:
              self.stream = input(self.args.readline_prompt) + '\n'
              if self.repl.paste_mode:
                while True:
                  line = input()
                  if line.strip() == '/paste off':
                    break
                  self.repl.buffers[IN] += line + '\n'
                self.stream = ' '.join(['/paste off'])
          tree = PARSER.parse(self.stream)
          dbg(tree, self)
          self.repl.visit(tree)
          if self.args.readline_history:
            write_history_file(self.args.readline_history)
        except (ValueError, RuntimeError, FileNotFoundError, LarkError) as e:
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

  def set_options(self, opt:ActorOptions) -> None:
    pass

  def get_options(self)->ActorOptions:
    return ActorOptions.init()
