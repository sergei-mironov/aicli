from gnureadline import (parse_and_bind, clear_history, read_history_file,
                         write_history_file, set_completer, set_completer_delims)
from lark import Lark, Token
from lark.exceptions import LarkError
from lark.visitors import Interpreter
from dataclasses import dataclass
from typing import Any
from copy import copy
from sys import stdout
from collections import defaultdict
from os import system, chdir, environ, getcwd, listdir
from os.path import expanduser, abspath, sep, join, isfile, isdir, split, dirname
from io import StringIO
from pdb import set_trace as ST
from subprocess import run, PIPE

from ..types import (Actor, ActorName, ActorOptions, Intention, Utterance,
                     Conversation, ActorView, ModelName, Modality)

from ..utils import (info, err, with_sigint, dbg, cont2strm, version, sys2exitcode, WLState,
                     wraplong, warn, onematch, expanddir)

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
CMD_PIPE = "/pipe"
CMD_VERSION = "/version"
CMD_CD = "/cd"
CMD_PASTE = "/paste"
CMD_PWD = "/pwd"  # Added the command for printing the current directory

def _mkref(tail):
  return {
    " verbatim:":{"STRING":tail},
    " file:":{"FILE":tail},
    " bfile:":{"FILE":tail},
    " buffer:":{"BUFFER":tail}}

REF = _mkref({})
REF_REF = _mkref(REF)
REF_REF_REF = _mkref(REF_REF)

MODEL = { " openai:":{"gpt-4o":{}, "dall-e-2":{}, "dall-e-3":{}},
          " gpt4all:":{"FILE":{}},
          " dummy":{"dummy":{}} }

VBOOL = { " true":{}, " false":{}, " yes": {}, " no": {}, " on": {}, " off": {}, " 1": {}, " 0":{} }

COMPLETION = {
  CMD_VERSION: {},
  CMD_DBG:     {},
  CMD_RESET:   {},
  CMD_ECHO:    {},
  CMD_ASK:     {},
  CMD_HELP:    {},
  CMD_EXIT:    {},
  CMD_PASTE:   VBOOL,
  CMD_MODEL:   MODEL,
  CMD_READ:    {},
  CMD_SET: {
    " model": {
      " modality":  { " modality_string": {}},
      " apikey":    REF,
      " imgsz":     {" string": {}},
      " temp":      {" FLOAT":  {}, " default": {}},
      " nt":        {" NUMBER": {}, " default": {}},
      " verbosity": {" NUMBER": {}, " default": {}},
      " imgnum":    {" NUMBER": {}, " default": {}},
      " imgdir":    {" string": {}, " default": {}},
      " modeldir":  {" string": {}, " default": {}},
    },
    " terminal": {
      " rawbin": VBOOL,
      " prompt": {" string": {}},
      " width": {" NUMBER": {}, " default": {}},
      " verbosity": {" NUMBER": {}, " default": {}},
    }
  },
  CMD_CP:      REF_REF,
  CMD_APPEND:  REF_REF,
  CMD_CAT:     REF,
  CMD_CLEAR:   REF,
  CMD_SHELL:   REF,
  CMD_PIPE:    REF_REF_REF,
  CMD_CD:      REF,
  CMD_PWD:     {}
}

SCHEMAS = [str(k).strip().replace(':','') for k in REF.keys()]
PROVIDERS = [str(p).strip().replace(':','') for p in MODEL.keys()]

CMDHELP = {
  CMD_APPEND:  ("REF REF",       "Append a file, a buffer or a constant to a file or to a buffer."),
  CMD_ASK:     ("",              "Ask the currently-active actor to repond."),
  CMD_CAT:     ("REF",           "Print a file or buffer to STDOUT."),
  CMD_CD:      ("REF",           "Change the current directory to the specified path"),
  CMD_CLEAR:   ("",              "Clear the buffer named `ref_string`."),
  CMD_CP:      ("REF REF",       "Copy a file, a buffer or a constant into a file or into a buffer."),
  CMD_DBG:     ("",              "Run the Python debugger"),
  CMD_ECHO:    ("",              "Echo the following line to STDOUT"),
  CMD_EXIT:    ("",              "Exit"),
  CMD_HELP:    ("",              "Print help"),
  CMD_MODEL:   ("PROVIDER:NAME", "Set the current model to `model_string`. Allocate the model on first use."),
  CMD_PASTE:   ("BOOL",          "Enable or disable paste mode."),
  CMD_READ:    ("WHERE",         "Reads the content of the 'IN' buffer into a special variable."),
  CMD_RESET:   ("",              "Reset the conversation and all the models"),
  CMD_SET:     ("WHAT",          "Set terminal or model option, check the Grammar for a full list of options."),
  CMD_SHELL:   ("REF",           "Run a system shell command."),
  CMD_PIPE:    ("REF REF REF",   "Run a system shell command, piping its input and output"),
  CMD_VERSION: ("",              "Print version"),
  CMD_PWD:     ("",              "Print the current working directory."),
}

GRAMMAR = fr"""
  start: (escape | command | comment | text)? (escape | command | comment | text)*
  # Escape disable any special meaning of one next symbol.
  escape: ESCAPE
  # Comments start from `#` and last until the end of the line.
  comment: COMMENT
  # Commands are `/` followed by one of the pre-defined words:
  command.1: /\{CMD_VERSION}/ | \
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
                                              /imgdir/ / +/ (string | DEF) | \
                                              /modeldir/ / +/ (string | DEF) | \
                                              /verbosity/ / +/ (NUMBER | DEF) | \
                                              /modality/ / +/ (MODALITY | DEF) | \
                                              /imgnum/ / +/ (NUMBER | DEF)) | \
                               (/term/ | /terminal/) / +/ (/rawbin/ / +/ BOOL | \
                                                           /prompt/ / +/ string | \
                                                           /width/ / +/ (NUMBER | DEF) | \
                                                           /verbosity/ / +/ (NUMBER | DEF))) | \
             /\{CMD_CP}/ / +/ ref / +/ ref | \
             /\{CMD_APPEND}/ / +/ ref / +/ ref | \
             /\{CMD_CAT}/ / +/ ref | \
             /\{CMD_CLEAR}/ / +/ ref | \
             /\{CMD_SHELL}/ / +/ ref | \
             /\{CMD_PIPE}/ / +/ ref / +/ ref / +/ ref | \
             /\{CMD_CD}/ / +/ ref | \
             /\{CMD_PASTE}/ / +/ BOOL | \
             /\{CMD_PWD}/
  # Everything else is a regular text.
  text: TEXT

  # Strings can start and end with a double-quote. Unquoted strings should not contain spaces.
  string:  "\"" "\"" | "\"" STRING_QUOTED "\"" | STRING_UNQUOTED

  # Model references are strings with the provider prefix
  model_ref: (PROVIDER ":")? string ("(" ID ")")?

  # References mention locations which could be either a file (`file:path/to/file`), a binary file
  # (`bfile:path/to/file`), a named memory buffer (`buffer:name`) or a read-only string constant
  # (`verbatim:ABC`).
  ref: (SCHEMA ":")? string -> ref | \
       (/file/ | /bfile/) (/\(/ | /\(/ / +/) ref (/\)/ | / +/ /\)/) -> ref_file

  # Base token types
  ESCAPE.5: /\\./
  SCHEMA.4: {'|'.join([f"/{s}/" for s in SCHEMAS])}
  PROVIDER.4: {'|'.join([f"/{p}/" for p in PROVIDERS])}
  STRING_QUOTED.3: /[^"]+/
  STRING_UNQUOTED.3: /[^"\(\)][^ \(\)\n]*/
  TEXT.0: /([^#](?![\/]))*[^\/#]/
  ID: /[a-zA-Z_][a-zA-Z0-9_]*/
  NUMBER: /[0-9]+/
  FLOAT: /[0-9]+\.[0-9]*/
  DEF: "default"
  BOOL: {'|'.join(['/'+str(k).strip()+'/' for k in VBOOL.keys()])}
  MODALITY: /img/ | /text/
  COMMENT: "#" /[^\n]*/
"""

PARSER = Lark(GRAMMAR, start='start', propagate_positions=True)

def is_default(val:Token)->bool:
  return str(val) in {"def","default"}

def as_float(val:Token, default:float|None=None)->float|None:
  assert val.type == 'FLOAT' or is_default(val), val
  return float(val) if not is_default(val) else default

def as_int(val:Token, default:int|None=None)->int|None:
  assert val.type == 'NUMBER' or is_default(val), val
  return int(val) if not is_default(val) else default

def as_str(val:Token, default:int|None=None)->int|None:
  assert isinstance(val,str) or is_default(val), val
  return str(val) if not is_default(val) else default

def as_bool(val:Token):
  assert val.type == 'BOOL', val
  if str(val) in ['true','yes','1','on']:
    return True
  elif str(val) in ['false','no','0','off']:
    return False
  else:
    raise ValueError(f"Invalid boolean value {val}")

def as_modality(pval:Token, default:Modality|None=None)->Modality|None:
  if is_default(pval):
    return default
  else:
    if str(pval) == 'img':
      return Modality.Image
    elif str(pval) == 'text':
      return Modality.Text
    else:
      raise ValueError(f"Invalid modality {pval}")

def ref_write(ref, val:list[str|bytes], buffers, append:bool=False):
  schema, name = ref
  a = "a" if append else ""
  if schema == 'file':
    try:
      with open(name, f"w{a}") as f:
        for cf in val:
          f.write(cf.encode('utf-8') if isinstance(v, bytes) else cf)
    except Exception as err:
      raise ValueError(str(err)) from err
  elif schema == 'bfile':
    try:
      with open(name, f"bw{a}") as f:
        for cf in val:
          f.write(cf if isinstance(cf,bytes) else cf.decode())
    except Exception as err:
      raise ValueError(str(err)) from err
  elif schema == 'buffer':
    if append:
      buffers[name.lower()].extend(val)  # Changed from += to extend
    else:
      buffers[name.lower()] = val
  else:
    raise ValueError(f"Unsupported target schema '{schema}'")

def ref_read(ref, buffers)->list[str|bytes]:
  schema, name = ref
  if schema=="verbatim":
    return [name]
  elif schema in ["file", "bfile"]:
    try:
      mode = "rb" if schema == "bfile" else "r"
      with open(expanduser(name), mode) as f:
        data = f.read().strip()
        return [data]
    except Exception as err:
      raise ValueError(str(err)) from err
  elif schema == 'buffer':
    return buffers[name.lower()]
  else:
    raise ValueError(f"Unsupported reference schema '{schema}'")

def ref_quote(ref:str, prefixes:list[str])->str:
  for p in [(p+':') for p in prefixes]:
    if ref.startswith(p) and (' ' in ref[len(p):]):
      return f"{p}\"{ref[len(p):]}\""
  return ref

def buffer2str(buffer:list[str|bytes]) -> str:
  """Convert a list of strings or bytes into a single string. Convert bytes to strings using
  utf-8."""
  return ''.join(item if isinstance(item, str) else item.decode('utf-8') for item in buffer)

def buffer2bytes(buffer:list[str|bytes]) -> bytes:
  """Convert a list of strings or bytes into a single bytes object. Convert strings to bytes using
  utf-8."""
  return b''.join(item if isinstance(item, bytes) else item.encode('utf-8') for item in buffer)

@dataclass
class InterpreterPause(Exception):
  unparsed:int
  utterance:Utterance

IN='in'
OUT='out'

class Repl(Interpreter):
  def __init__(self, owner:"UserActor"):
    self.owner = owner
    self.buffers:dict[str,list[str|bytes]] = defaultdict(list)  # Changed type to list[str]
    self.av = None
    self.actor_next = None
    self.rawbin = False
    self.ref_schema_default = "verbatim"
    self._reset()
    self.paste_mode = False
    self.readline_prompt = owner.args.readline_prompt
    self.wlstate = WLState(None)

  def _check_next_actor(self):
    if self.actor_next is None:
      raise RuntimeWarning("No model is active, use /model first")

  def _reset(self):
    self.in_echo = 0
    self.buffers[IN] = []
    self.buffers[OUT] = []

  def _print(self, s=None, flush=False, end='\n'):
    wraplong((s or '') + end, self.wlstate, lambda s: print(s, end='', flush=True), flush=flush)

  def reset(self):
    old_message = buffer2str(self.buffers[IN])
    self._reset()
    if len(old_message) > 0:
      self.owner.info("Message buffer is now empty")

  def _finish_echo(self):
    if self.in_echo:
      self._print(flush=True)
    self.in_echo = 0

  def string(self, tree)->str:
    if tree.children:
      assert len(tree.children) == 1, tree
      assert tree.children[0].type in ('STRING_QUOTED','STRING_UNQUOTED'), tree
      if tree.children[0].type == 'STRING_UNQUOTED':
        self._check_no_commands(tree.children[0].value, hint='string constant')
      return tree.children[0].value
    else:
      return ""

  def ref(self, tree):
    val = self.visit_children(tree)
    return (str(val[0]), val[1]) if len(val) == 2 else (self.ref_schema_default, val[0])

  def model_ref(self, tree):
    val = self.visit_children(tree)
    if len(val) == 1:
      return ModelName(str(val[0]), "default", None)
    elif len(val) == 2:
      return ModelName(str(val[0]), str(val[1]), None)
    elif len(val) == 3:
      return ModelName(str(val[0]), str(val[1]), str(val[2]))
    else:
      raise ValueError(f"Invalid model reference: '{val}'")

  def ref_file(self, tree):
    args = self.visit_children(tree)
    val = buffer2str(ref_read(args[2], self.buffers))
    return (str(args[0]), val.strip())

  def bool(self, tree):
    val = self.visit_children(tree)[0]
    if val in ['true', 'yes', '1']:
      return [True]
    elif val in ['false', 'no', '0']:
      return [False]
    else:
      raise ValueError(f"Invalid boolean value {val}")

  def command(self, tree):
    self._finish_echo()
    command = tree.children[0].value
    opts = self.av.options
    if command == CMD_ECHO:
      self.in_echo = 1
    elif command == CMD_ASK:
      try:
        val = self.visit_children(tree)
        self._check_next_actor()
        raise InterpreterPause(
          unparsed=tree.meta.end_pos,
          utterance=Utterance.init(
            name=self.owner.name,
            contents=self.buffers[IN],
            intention=Intention.init(
              actor_next=self.actor_next,
              actor_updates=self.av,
            )
          )
        )
      finally:
        self.buffers[IN] = []
    elif command == CMD_HELP:
      self._print(self.owner.args.help)
      self._print("Command-line grammar:")
      self._print(GRAMMAR)
      self._print("Commands summary:\n")
      self._print('\n'.join([f"  {c:12s} {h[0]:15s} {h[1]}" for c,h in CMDHELP.items()]), flush=True)
    elif command == CMD_EXIT:
      raise InterpreterPause(
        unparsed=tree.meta.end_pos,
        utterance=Utterance.init(
          name=self.owner.name,
          intention=Intention.init(exit_flag=True, actor_updates=self.av)
        )
      )
    elif command == CMD_MODEL:
      res = self.visit_children(tree)
      if len(res) > 2:
        assert isinstance(res[2], ModelName), f"{res[2]} is not a ModelName"
        name = res[2]
        opt = opts.get(name, ActorOptions.init())
        self.owner.info(f"Setting target actor to '{name.repr()}'")
        opts[name] = opt
        self.actor_next = name
      else:
        raise ValueError("Invalid model name format")
    elif command == CMD_SET:
      self.ref_schema_default = "verbatim"
      args = self.visit_children(tree)
      section, pname, pval = args[2], args[4], args[6]
      if section == 'model':
        self._check_next_actor()
        if pname == 'apikey':
          if not isinstance(pval, tuple) or len(pval) != 2:
            raise ValueError("Model API key should be formatted as `schema:value`")
          opts[self.actor_next].apikey = buffer2str(ref_read(pval, self.buffers))
          self.owner.info(f"Setting model API key to the contents of '{pval[0]}:{pval[1]}'")
        elif pname in ['t', 'temp']:
          val = as_float(pval)
          opts[self.actor_next].temperature = val
          self.owner.info(f"Setting model temperature to '{val or 'default'}'")
        elif pname in ['nt', 'nthreads']:
          val = as_int(pval)
          opts[self.actor_next].num_threads = val
          self.owner.info(f"Setting model number of threads to '{val or 'default'}'")
        elif pname == 'imgsz':
          opts[self.actor_next].imgsz = pval
          self.owner.info(f"Setting model image size to '{opts[self.actor_next].imgsz}'")
        elif pname == 'imgdir':
          val = as_str(pval)
          opts[self.actor_next].image_dir = onematch(expanddir(val)) if val else None
          self.owner.info(f"Setting model image dir to '{opts[self.actor_next].image_dir}'")
        elif pname == 'modeldir':
          val = as_str(pval)
          opts[self.actor_next].model_dir = onematch(expanddir(val)) if val else None
          self.owner.info(f"Setting model dir to '{opts[self.actor_next].model_dir}'")
        elif pname == 'imgnum':
          opts[self.actor_next].imgnum = as_int(pval)
          self.owner.info(f"Setting model image number to '{opts[self.actor_next].imgnum}'")
        elif pname == 'verbosity':
          val = as_int(pval)
          opts[self.actor_next].verbose = val
          self.owner.info(f"Setting actor verbosity to '{val}'")
        elif pname == 'modality':
          mod = as_modality(pval)
          opts[self.actor_next].modality = mod
          self.owner.info(f"Setting model modality to '{mod}'")
        else:
          raise ValueError(f"Unknown actor parameter '{pname}'")
      elif section in ['term', 'terminal']:
        if pname == 'rawbin':
          val = as_bool(pval)
          self.owner.info(f"Setting terminal raw binary mode to '{val}'")
          self.rawbin = val
        elif pname == 'prompt':
          self.readline_prompt = pval
          self.owner.info(f"Setting terminal prompt to '{self.readline_prompt}'")
        elif pname == 'width':
          self.wlstate.max_width = as_int(pval, None)
          self.owner.info(f"Setting terminal width to '{self.wlstate.max_width}'")
        elif pname == 'verbosity':
          val = as_int(pval)
          self.owner.opt.verbose = val
          self.owner.info(f"Setting terminal verbosity to '{val}'")
        else:
          raise ValueError(f"Unknown terminal parameter '{pname}'")
      else:
        raise ValueError(f"Unknown set section '{section}'")
    elif command == CMD_READ:
      args = self.visit_children(tree)
      section, pname, pval = args[2], args[4], buffer2str(self.buffers[IN]).strip()
      assert section == 'model'
      self._check_next_actor()
      if pname == 'prompt':
        opts[self.actor_next].prompt = pval
        self.owner.info(f"Setting actor prompt to '{pval[:10]}...'")
      else:
        raise ValueError(f"Unknown read parameter '{pname}'")
      self.buffers[IN] = []
    elif command == CMD_CLEAR:
      self.ref_schema_default = "buffer"
      args = self.visit_children(tree)
      (schema, name) = args[2]
      if schema != 'buffer':
        raise ValueError(f'Required reference to buffer, not {schema}')
      self.owner.info(f"Clearing buffer \"{name.lower()}\"")
      ref_write((schema, name), [], self.buffers, append=False)
    elif command == CMD_RESET:
      self.owner.info("Resetting conversation history and clearing message buffer")
      self.reset()
      raise InterpreterPause(
        unparsed=tree.meta.end_pos,
        utterance=Utterance.init(
          name=self.owner.name,
          intention=Intention.init(reset_flag=True)
        )
      )
    elif command == CMD_DBG:
      self.owner.info("Calling Python debugger")
      raise InterpreterPause(
        unparsed=tree.meta.end_pos,
        utterance=Utterance.init(
          name=self.owner.name,
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
      self.owner.info(f"{'Appended' if append else 'Copied'} from {sref} to {dref}")
    elif command == CMD_CAT:
      self.ref_schema_default = "buffer"
      args = self.visit_children(tree)
      ref = args[2]
      val = buffer2str(ref_read(ref, self.buffers))
      self._print(val, flush=True)
    elif command == CMD_SHELL:
      self.ref_schema_default = "buffer"
      args = self.visit_children(tree)
      ref = args[2]
      cmd = buffer2str(ref_read(ref, self.buffers)).replace('\n',' ').strip()
      retcode = sys2exitcode(system(cmd))
      self.owner.info(f"Shell command '{cmd}' exited with code {retcode}")
      if ref == ('buffer','in'):
        ref_write(('buffer','in'), [], self.buffers, append=False)
    elif command == CMD_PIPE:
      self.ref_schema_default = "buffer"
      args = self.visit_children(tree)
      ref_cmd, ref_inp, ref_out = args[2], args[4], args[6]
      cmd = buffer2str(ref_read(ref_cmd, self.buffers))
      inp = buffer2bytes(ref_read(ref_inp, self.buffers))
      runres = run(cmd, input=inp, text=False, shell=True, stdout=PIPE, stderr=PIPE)
      retcode = runres.returncode
      try:
        out = runres.stdout.decode('utf-8')
      except UnicodeDecodeError:
        out = runres.stdout
      ref_write(ref_out, out, self.buffers, append=False)
      self.owner.info(f"Pipe command '{cmd}' exited with code {retcode}")
      if inp == ('buffer','in') or cmd == ('buffer','in'):
        ref_write(('buffer','in'), [], self.buffers, append=False)
    elif command == CMD_CD:
      self.ref_schema_default = "verbatim"
      args = self.visit_children(tree)
      ref = args[2]
      path = buffer2str(ref_read(ref, self.buffers))
      try:
        chdir(path)
        self.owner.info(f"Changing current directory to '{path}'")
      except Exception as err:
        raise ValueError(str(err)) from err
    elif command == CMD_PWD:
      self._print(getcwd(), flush=True)
    elif command == CMD_VERSION:
      self._print(version(), flush=True)
    elif command == CMD_PASTE:
      args = self.visit_children(tree)
      val = as_bool(args[2])
      if val:
        self.owner.info("Entering paste mode. Type '/paste off' to finish.")
      else:
        self.owner.info("Exiting paste mode.")
      self.paste_mode = val
    else:
      raise ValueError(f"Unknown command: {command}")

  def _check_no_commands(self, text, hint):
    commands = []
    for cmd in list(CMDHELP.keys()):
      if cmd in text:
        commands.append(cmd)
    if commands:
      self.owner.warn(f"{', '.join(['`'+c+'`' for c in commands])} were parsed as a {hint}")

  def text(self, tree):
    text = tree.children[0].value
    if self.in_echo:
      if self.in_echo == 1:
        self._print(text.strip(), end='')
        self.in_echo = 2
      else:
        self._print(text, end='')
    else:
      self._check_no_commands(text, hint='text')
      self.buffers[IN].append(text)

  def escape(self, tree):
    text = tree.children[0].value[1:]
    if self.in_echo:
      self._print(text)
    else:
      self.buffers[IN].append(text)

  def comment(self, tree):
    pass

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

    self.args = args
    if args.readline_history is None:
      args.readline_history = environ.get("AICLI_HISTORY")
    if args.readline_history is not None:
      args.readline_history = abspath(expanduser(args.readline_history))

    header = StringIO()
    rcnames = environ.get('AICLI_RC', args.rc)
    if rcnames is not None and len(rcnames)>0 and rcnames!='none':
      for line in self._read_configs(rcnames.split(',')):
        header.write(line+'\n')
    else:
      self.info("Skipping configuration files")
    if args.model is not None:
      header.write(f"/model {ref_quote(args.model, PROVIDERS)}\n")
    if args.model_apikey is not None:
      header.write(f"/set model apikey {ref_quote(args.model_apikey, SCHEMAS)}\n")
    if args.image_dir is not None:
      header.write(f"/set model imgdir \"{args.image_dir}\"\n")
    if args.model_dir is not None:
      header.write(f"/set model modeldir \"{args.model_dir}\"\n")

    for file in args.filenames:
      with open(file) as f:
        self.info(f"Reading {file}")
        header.write(f.read())

    set_completer_delims('')
    set_completer(self._complete)
    parse_and_bind('tab: complete')
    parse_and_bind(f'"{args.readline_key_send}": "{CMD_ASK}\n"')
    hint = args.readline_key_send.replace('\\', '')
    self.info(f"Type /help or a question followed by the /ask command (or by pressing "
          f"`{hint}` key).")

    self._reload_history()

    self.stream = header.getvalue()
    self.repl = Repl(self)
    self.batch_mode = len(args.filenames) > 0
    self.reset()

  def info(self, message: str):
    info(message, self)

  def warn(self, message: str):
    warn(message, self)

  def _reload_history(self):
    if self.args.readline_history is not None:
      try:
        clear_history()
        read_history_file(self.args.readline_history)
        info(f"History file loaded", self)
      except FileNotFoundError:
        info(f"History file not loaded", self)
    else:
      info(f"History file is not used", self)

  def _read_configs(self, rcnames:list[str])->list[str]:
    acc = []
    current_dir = abspath(getcwd())
    path_parts = current_dir.split(sep)
    last_dir = None
    for depth in range(2, len(path_parts) + 1):
      directory = sep.join(path_parts[:depth])
      for fn in rcnames:
        candidate_file = join(directory, fn)
        if isfile(candidate_file):
          with open(candidate_file, 'r') as file:
            info(f"Reading {candidate_file}", self)
            new_dir = dirname(candidate_file)
            if last_dir != new_dir:
              acc.append(f"{CMD_CD} \"{new_dir}\"")
              last_dir = new_dir
            for line in file.readlines():
              acc.append(line.strip())
            if last_dir != getcwd():
              acc.append(f"{CMD_CD} \"{getcwd()}\"")
              last_dir = getcwd()
    return acc

  def _complete(self, text:str, state:int) -> str|None:
    current_dict = COMPLETION
    candidates = []
    prefix = ''

    while True:
      matched = None
      if list(current_dict.keys()) == ['FILE']:
        dnext = current_dict['FILE']
        fname = text.split()[0] if text.split() else None
        if isfile(fname):
          text = text[len(fname):]
          prefix += fname
          current_dict = dnext
          continue
        else:
          path, partial = split(fname)
          if not path:
            path = '.'
          try:
            entries = listdir(path)
            file_dict = {entry: dnext for entry in entries if isfile(join(path, entry))}
            dir_dict = {entry: {'FILE': dnext} for entry in entries if isdir(join(path, entry))}
            current_dict = {**file_dict, **dir_dict}
          except FileNotFoundError:
            current_dict = {}
          candidates = [join(path, k) for k in current_dict if k.startswith(partial)]
          break
      elif list(current_dict.keys()) == ['BUFFER']:
        buf = text.split()[0] if text.split() else None
        if buf and (buf in self.repl.buffers):
          text = text[len(buf):]
          prefix += buf
          current_dict = current_dict['BUFFER']
          continue
        else:
          candidates = [n for n in self.repl.buffers.keys() if n.startswith(text)]
          current_dict = {}
          break
      else:
        for key in current_dict.keys():
          if text.startswith(str(key)):
            matched = str(key)
            break
        if matched:
          text = text[len(matched):]
          prefix += matched
          current_dict = current_dict[matched]
          continue
        elif isinstance(current_dict, dict):
          candidates = [k for k in current_dict if k.startswith(text)]
          break
        else:
          break
    if not candidates:
      candidates = list(current_dict.keys())
    candidates.sort()
    try:
      return prefix + candidates[state]
    except IndexError:
      return None

  def _sync(self, av:ActorView, cnv:Conversation):
    assert self.cnv_top <= len(cnv.utterances)
    if self.repl.av is None:
      self.repl.av = av
    for i in range(self.cnv_top, len(cnv.utterances)):
      u:Utterance = cnv.utterances[i]
      if u.actor_name != self.name:
        need_eol = False
        buffer_out = []
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
              self.info("Binary stream has been saved to file")
              out_content = s.suggested_fname
              buffer_out.append(out_content + ' ')
              self.repl._print(f"{out_content}", flush=True)
            else:
              for token in s.gen():
                if isinstance(token, bytes):
                  need_eol = True
                  stdout.buffer.write(token)
                  stdout.buffer.flush()
                elif isinstance(token, str):
                  need_eol = not token.rstrip(' ').endswith("\n")
                  # print(token, end='', flush=True)
                  # wraplong(token, self.repl.wlstate, lambda x: print(x, end=''))
                  self.repl._print(token, end='')
                buffer_out.append(token)
        self.repl.buffers[OUT] = buffer_out
        if need_eol:
          self.repl._print()
        self.repl._print(flush=True, end='')
      self.cnv_top += 1

  def reset(self):
    self.cnv_top = 0

  def _prompt(self):
    return self.repl.readline_prompt

  def _paste_prompt(self):
    return 'P' + self._prompt() if self._prompt() else ''

  def react(self, av:ActorView, cnv:Conversation) -> Utterance:
    # FIMXE: A minor problem here in the paste_mode [1]: interpreter eats the
    # input first, and handles the paste mode after that. It should raise
    # InterpreterPause instead.
    self._sync(av, cnv)
    try:
      while True:
        try:
          if self.stream == '':
            if self.batch_mode and not self.args.keep_running:
              break
            else:
              self.stream = input(self._prompt()) + '\n'
          tree = PARSER.parse(self.stream)
          dbg(tree, self)
          self.repl.visit(tree)
          while self.repl.paste_mode: # [1]
            line = input(self._paste_prompt())
            if line.strip() == f'{CMD_PASTE} off':
              self.repl.paste_mode = False
            else:
              self.repl.buffers[IN].append(line + '\n')
          if self.args.readline_history is not None:
            write_history_file(self.args.readline_history)
        except (RuntimeWarning,) as e:
          warn(str(e), actor=self)
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

