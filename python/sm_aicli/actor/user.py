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
from os.path import expanduser, sep, abspath, join, isfile, isdir, split, dirname
from io import StringIO
from pdb import set_trace as ST
from subprocess import run, PIPE

from ..types import (Stream, Logger, Actor, ActorDesc, ActorName, ActorOptions, Intention,
                     Utterance, Conversation, ActorState, ModelName, Modality, QuotedString,
                     UnquotedString, Parser, File, ContentItem, Reference, LocalReference,
                     LocalContent, RemoteReference, ParsingResults, RecordingParams, Recorder)

from ..utils import (IterableStream, ConsoleLogger, with_sigint, version, sys2exitcode, WLState,
                     wraplong, onematch, expanddir, info, set_global_verbosity, traverse_stream)

CMD_APPEND = "/append"
CMD_ASK  = "/ask"
CMD_ANS  = "/ans"
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
CMD_REF = "/ref"

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
      " replay":    {" BOOL":   {}, " default": {}},
      " nt":        {" NUMBER": {}, " default": {}},
      " verbosity": {" NUMBER": {}, " default": {}},
      " seed":      {" NUMBER": {}, " default": {}},
      " imgnum":    {" NUMBER": {}, " default": {}},
      " imgdir":    {" string": {}, " default": {}},
      " modeldir":  {" string": {}, " default": {}},
      " proxy":     {" string": {}, " default": {}},
    },
    " terminal": {
      " rawbin": VBOOL,
      " prompt": {" string": {}},
      " width": {" NUMBER": {}, " default": {}},
      " verbosity": {" NUMBER": {}, " default": {}},
      " recording": REF,
    }
  },
  CMD_CP:      REF_REF,
  CMD_APPEND:  REF_REF,
  CMD_CAT:     REF,
  CMD_CLEAR:   REF,
  CMD_SHELL:   REF,
  CMD_PIPE:    REF_REF_REF,
  CMD_CD:      REF,
  CMD_PWD:     {},
  CMD_REF:     {" string": {" string": {}}}
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
  CMD_REF:     ("STR STR",       "Insert a reference to a remote object"),
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
                                              /seed/ / +/ (NUMBER | DEF) | \
                                              /replay/ / +/ (BOOL | DEF) | \
                                              /modality/ / +/ (MODALITY | DEF) | \
                                              /proxy/ / +/ (string | DEF) | \
                                              /imgnum/ / +/ (NUMBER | DEF)) | \
                               (/term/ | /terminal/) / +/ (/rawbin/ / +/ BOOL | \
                                                           /prompt/ / +/ string | \
                                                           /recording/ / +/ ref | \
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
             /\{CMD_REF}/ / +/ string / +/ string | \
             /\{CMD_PWD}/
  # Everything else is a regular text.
  text: TEXT

  # Strings can start and end with a double-quote. Unquoted strings should not contain spaces.
  string:  "\"" "\"" | "\"" STRING_QUOTED "\"" | \
           "'" "'" | "'" STRING_QUOTED2 "'" | STRING_UNQUOTED

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
  STRING_QUOTED2.3: /[^']+/
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
          f.write(cf.encode('utf-8') if isinstance(cf, bytes) else cf)
    except Exception as err:
      raise ValueError(str(err)) from err
  elif schema == 'bfile':
    try:
      with open(name, f"bw{a}") as f:
        for cf in val:
          f.write(cf if isinstance(cf, bytes) else cf.decode())
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

def ref2str(ref:Reference) -> str:
  match ref:
    case RemoteReference():
      return f"/ref \"{ref.mimetype}\" \"{ref.url}\""
    case LocalReference():
      return f"/ref \"{ref.mimetype}\" \"{ref.path}\""
    case _:
      raise ValueError(f"Unsupported reference: {ref}")


def buffer2str(buffer:LocalContent) -> str:
  """Convert a list of strings or bytes into a single string. Convert bytes to strings using
  utf-8."""
  acc = []
  for item in buffer:
    match item:
      case str():
        acc.append(item)
      case bytes():
        acc.append(item.decode('utf-8'))
      case Reference():
        acc.append(ref2str(item))
      case _:
        raise ValueError(f"Unsupported buffer item: {item}")
  return ''.join(acc)


def buffer2bytes(buffer:LocalContent) -> bytes:
  """Convert a list of strings or bytes into a single bytes object. Convert strings to bytes using
  utf-8."""
  acc = []
  for item in buffer:
    match item:
      case str():
        acc.append(item.encode('utf-8'))
      case bytes():
        acc.append(item)
      case _:
        raise ValueError(f"Unsupported buffer item: {item}")
  return b''.join(acc)


def bufferadd(buffer:LocalContent, val:str|bytes) -> None:
  if len(buffer)==0 or not isinstance(buffer[-1], type(val)):
    buffer.append(type(val)())
  buffer[-1] += val


class UserRecorder(Recorder):
  def __init__(self):
    self.recfile = None
  def record(self, chunk:str) -> None:
    if self.recfile is not None:
      self.recfile.write(chunk)
      self.recfile.flush()
  def update_params(self, recording:RecordingParams) ->None:
    if self.recfile is not None:
      self.recfile.write(f"{CMD_SET} model replay off\n")
      self.recfile.close()
    if recording.filename is not None:
      self.recfile = open(recording.filename, "w")
      self.recfile.write(f"{CMD_SET} model replay on\n")
      self.recfile.flush()
    else:
      self.recfile = None

@dataclass
class InterpreterPause(Exception):
  unparsed:int
  utterance:Utterance|None=None
  recording:RecordingParams|None=None
  paste_mode:bool|None=None

IN='in'
OUT='out'

class Repl(Interpreter):
  def __init__(self, owner:"UserActor", logger:Logger):
    self.owner = owner
    self.buffers:dict[str,LocalContent] = defaultdict(list)  # Changed type to list[str]
    self.opts: ActorDesc|None = None
    self.actor_next = None
    self.rawbin = False
    self._reset()
    self.readline_prompt = owner.args.readline_prompt
    self.wlstate = WLState(None)
    self.logger = logger

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
      self.logger.info("Message buffer is now empty")

  def _finish_echo(self):
    if self.in_echo:
      self._print(flush=True, end='')
    self.in_echo = 0

  def string(self, tree)->str:
    if tree.children:
      assert len(tree.children) == 1, tree
      assert tree.children[0].type in ('STRING_QUOTED2','STRING_QUOTED','STRING_UNQUOTED'), tree
      if tree.children[0].type == 'STRING_UNQUOTED':
        self._check_no_commands(tree.children[0].value, hint='string constant')
        return UnquotedString(tree.children[0].value)
      else:
        return QuotedString(tree.children[0].value)
    else:
      return QuotedString("")

  def ref(self, tree):
    val = self.visit_children(tree)
    if len(val) == 2:
      return (str(val[0]), val[1])
    else:
      if isinstance(val[0], QuotedString):
        return ("verbatim", val[0])
      else:
        return ("buffer", val[0])

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
    opts = self.opts
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
            contents=IterableStream(self.buffers[IN]),
            intention=Intention.init(
              actor_next=self.actor_next,
              actor_updates=self.opts,
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
          intention=Intention.init(exit_flag=True, actor_updates=self.opts)
        )
      )
    elif command == CMD_MODEL:
      res = self.visit_children(tree)
      if len(res) > 2:
        assert isinstance(res[2], ModelName), f"{res[2]} is not a ModelName"
        name = res[2]
        opt = opts.get(name, ActorOptions.init())
        self.logger.info(f"Setting target actor to '{name.repr()}'")
        opts[name] = opt
        self.actor_next = name
      else:
        raise ValueError("Invalid model name format")
    elif command == CMD_SET:
      args = self.visit_children(tree)
      section, pname, pval = args[2], args[4], args[6]
      if section == 'model':
        self._check_next_actor()
        if pname == 'apikey':
          if not isinstance(pval, tuple) or len(pval) != 2:
            raise ValueError("Model API key should be formatted as `schema:value`")
          opts[self.actor_next].apikey = buffer2str(ref_read(pval, self.buffers))
          self.logger.info(f"Setting model API key to the contents of '{pval[0]}:{pval[1]}'")
        elif pname in ['t', 'temp']:
          val = as_float(pval)
          opts[self.actor_next].temperature = val
          self.logger.info(f"Setting model temperature to '{val or 'default'}'")
        elif pname in ['nt', 'nthreads']:
          val = as_int(pval)
          opts[self.actor_next].num_threads = val
          self.logger.info(f"Setting model number of threads to '{val or 'default'}'")
        elif pname == 'imgsz':
          opts[self.actor_next].imgsz = pval
          self.logger.info(f"Setting model image size to '{opts[self.actor_next].imgsz}'")
        elif pname == 'imgdir':
          val = as_str(pval)
          opts[self.actor_next].image_dir = onematch(expanddir(val)) if val else None
          self.logger.info(f"Setting model image dir to '{opts[self.actor_next].image_dir}'")
        elif pname == 'modeldir':
          val = as_str(pval)
          opts[self.actor_next].model_dir = onematch(expanddir(val)) if val else None
          self.logger.info(f"Setting model dir to '{opts[self.actor_next].model_dir}'")
        elif pname == 'imgnum':
          opts[self.actor_next].imgnum = as_int(pval)
          self.logger.info(f"Setting model image number to '{opts[self.actor_next].imgnum}'")
        elif pname == 'verbosity':
          val = as_int(pval)
          opts[self.actor_next].verbose = val
          self.logger.info(f"Setting actor verbosity to '{val}'")
        elif pname == 'seed':
          val = as_int(pval)
          opts[self.actor_next].seed = val
          self.logger.info(f"Setting actor seed to '{val}'")
        elif pname == 'modality':
          mod = as_modality(pval)
          opts[self.actor_next].modality = mod
          self.logger.info(f"Setting model modality to '{mod}'")
        elif pname == 'replay':
          val = as_bool(pval)
          opts[self.actor_next].replay = val
          self.logger.info(f"Setting model replay to '{val}'")
        elif pname == 'proxy':
          val = as_str(pval)
          opts[self.actor_next].proxy = val
          self.logger.info(f"Setting model proxy to '{val}'")
        else:
          raise ValueError(f"Unknown actor parameter '{pname}'")
      elif section in ['term', 'terminal']:
        if pname == 'rawbin':
          val = as_bool(pval)
          self.logger.info(f"Setting terminal raw binary mode to '{val}'")
          self.rawbin = val
        elif pname == 'prompt':
          self.readline_prompt = pval
          self.logger.info(f"Setting terminal prompt to '{self.readline_prompt}'")
        elif pname == 'width':
          self.wlstate.max_width = as_int(pval, None)
          self.logger.info(f"Setting terminal width to '{self.wlstate.max_width}'")
        elif pname == 'verbosity':
          val = as_int(pval)
          self.owner.opt.verbose = val
          set_global_verbosity(val)
          self.logger.info(f"Setting terminal verbosity to '{val}'")
        elif pname == 'recording':
          # val = as_ref(ref_read(pval, self.buffers))
          if pval[0]!='file':
            raise ValueError(f"Reference should be a file, not {pval}")
          self.logger.info(f"Setting terminal recording to '{pval}'")
          raise InterpreterPause(
            unparsed=tree.meta.end_pos,
            recording=RecordingParams(pval[1])
          )
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
        self.logger.info(f"Setting actor prompt to '{pval[:10]}...'")
      else:
        raise ValueError(f"Unknown read parameter '{pname}'")
      self.buffers[IN] = []
    elif command == CMD_CLEAR:
      args = self.visit_children(tree)
      (schema, name) = args[2]
      if schema != 'buffer':
        raise ValueError(f'Required reference to buffer, not {schema}')
      self.logger.info(f"Clearing buffer \"{name.lower()}\"")
      ref_write((schema, name), [], self.buffers, append=False)
    elif command == CMD_RESET:
      self.logger.info("Resetting conversation history and clearing message buffer")
      self.reset()
      raise InterpreterPause(
        unparsed=tree.meta.end_pos,
        utterance=Utterance.init(
          name=self.owner.name,
          intention=Intention.init(reset_flag=True)
        )
      )
    elif command == CMD_DBG:
      self.logger.info("Calling Python debugger")
      raise InterpreterPause(
        unparsed=tree.meta.end_pos,
        utterance=Utterance.init(
          name=self.owner.name,
          intention=Intention.init(dbg_flag=True)
        )
      )
    elif command in [CMD_CP, CMD_APPEND]:
      append = (command == CMD_APPEND)
      args = self.visit_children(tree)
      sref, dref = args[2], args[4]
      val = ref_read(sref, self.buffers)
      ref_write(dref, val, self.buffers, append=append)
      self.logger.info(f"{'Appended' if append else 'Copied'} from {sref} to {dref}")
    elif command == CMD_CAT:
      args = self.visit_children(tree)
      ref = args[2]
      val = buffer2str(ref_read(ref, self.buffers))
      self._print(val, flush=True)
    elif command == CMD_SHELL:
      args = self.visit_children(tree)
      ref = args[2]
      ref_cont = ref_read(ref, self.buffers)
      cmd = buffer2str(ref_cont).replace('\n',' ').strip()
      retcode = sys2exitcode(system(cmd))
      self.logger.info(f"Shell command '{cmd}' exited with code {retcode}")
      if ref == ('buffer','in'):
        ref_write(('buffer','in'), [], self.buffers, append=False)
    elif command == CMD_PIPE:
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
      ref_write(ref_out, [out], self.buffers, append=False)
      self.logger.info(f"Pipe command '{cmd}' exited with code {retcode}")
      if inp == ('buffer','in') or cmd == ('buffer','in'):
        ref_write(('buffer','in'), [], self.buffers, append=False)
    elif command == CMD_CD:
      args = self.visit_children(tree)
      ref = args[2]
      path = buffer2str(ref_read(ref, self.buffers))
      try:
        chdir(path)
        self.logger.info(f"Changing current directory to '{path}'")
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
        self.logger.info("Entering paste mode. Type '/paste off' to finish.")
      else:
        self.logger.info("Exiting paste mode.")
      raise InterpreterPause(
        unparsed=tree.meta.end_pos,
        paste_mode=val
      )
    elif command == CMD_REF:
      args = self.visit_children(tree)
      mimetype = as_str(args[2])
      url = as_str(args[4])
      ref = None
      if any(url.startswith(sch) for sch in ['http', 'https', 'ftp']):
        ref = RemoteReference(mimetype, url)
      else:
        ref = LocalReference(mimetype, url)
      assert ref is not None
      self.buffers[IN].append(ref)
    else:
      raise ValueError(f"Unknown command: {command}")

  def _check_no_commands(self, text, hint):
    commands = []
    for cmd in list(CMDHELP.keys()):
      if cmd in text:
        commands.append(cmd)
    if commands:
      self.logger.warn(f"{', '.join(['`'+c+'`' for c in commands])} were parsed as a {hint}")

  def text(self, tree):
    text = tree.children[0].value
    if self.in_echo:
      if self.in_echo == 1:
        self._print(text.lstrip(), end='')
        self.in_echo = 2
      else:
        self._print(text, end='')
    else:
      self._check_no_commands(text, hint='text')
      # self.buffers[IN].append(text)
      bufferadd(self.buffers[IN], text)

  def escape(self, tree):
    text = tree.children[0].value[1:]
    if self.in_echo:
      self._print(text)
    else:
      bufferadd(self.buffers[IN], text)

  def comment(self, tree):
    pass

  def visit(self, tree):
    self.in_echo = 0
    try:
      res = super().visit(tree)
    finally:
      self._finish_echo()
    return res


class ReplParser(Parser):
  def __init__(self, repl:Repl):
    self.repl = repl
  def parse(self, chunk:str) -> ParsingResults:
    try:
      tree = PARSER.parse(chunk)
      self.repl.logger.dbg(tree)
      self.repl.visit(tree)
    except InterpreterPause as p:
      return ParsingResults(chunk[p.unparsed:], p.utterance, p.recording, p.paste_mode)
    except (RuntimeWarning,) as e:
      self.repl.logger.warn(str(e))
    except (ValueError, RuntimeError, FileNotFoundError, LarkError) as e:
      self.repl.logger.err(str(e))
    return ParsingResults('', None)

class PasteModeReplParser(Parser):
  def __init__(self, repl:Repl):
    self.repl = repl
  def parse(self, chunk:str) -> ParsingResults:
    pattern = f'{CMD_PASTE} off'
    if (off_index := (chunk.index(pattern) if (pattern in chunk) else None)) is not None:
      return ParsingResults(chunk[off_index + len(pattern):], None, paste_mode=False)
    else:
      bufferadd(self.repl.buffers[IN], chunk)
      return ParsingResults('', None)


def read_configs(rcnames:list[str])->str:
  acc = StringIO()
  current_dir = abspath(getcwd())
  path_parts = current_dir.split(sep)
  last_dir = None
  for depth in range(2, len(path_parts) + 1):
    directory = sep.join(path_parts[:depth])
    for fn in rcnames:
      candidate_file = join(directory, fn)
      if isfile(candidate_file):
        with open(candidate_file, 'r') as file:
          info(f"Reading {candidate_file}")
          new_dir = dirname(candidate_file)
          if last_dir != new_dir:
            acc.write(f"{CMD_CD} \"{new_dir}\"\n")
            last_dir = new_dir
          for line in file.readlines():
            acc.write(line)
          if last_dir != getcwd():
            acc.write(f"{CMD_CD} \"{getcwd()}\"\n")
            last_dir = getcwd()
  return acc.getvalue()

def args2script(args, configs:str|None) -> str:
  header = StringIO()
  header.write(configs or "")
  if args.model is not None:
    header.write(f"/model {ref_quote(args.model, PROVIDERS)}\n")
  if args.model_apikey is not None:
    header.write(f"/set model apikey {ref_quote(args.model_apikey, SCHEMAS)}\n")
  if args.image_dir is not None:
    header.write(f"/set model imgdir \"{args.image_dir}\"\n")
  if args.model_dir is not None:
    header.write(f"/set model modeldir \"{args.model_dir}\"\n")
  if args.verbose is not None:
    header.write(f"/set terminal verbosity {int(args.verbose)}\n")


  for file in args.filenames:
    with open(file) as f:
      info(f"Reading {file}")
      header.write(f.read())
  return header.getvalue()


class UserActor(Actor):

  def __init__(self,
               name:ActorName,
               opt:ActorOptions,
               args:Any,
               file:File):
    super().__init__(name, opt)
    self.logger = ConsoleLogger(self)
    self.args = args

    # Setup Completion
    set_completer_delims('')
    set_completer(self._complete)
    parse_and_bind('tab: complete')
    parse_and_bind(f'"{args.readline_key_send}": "{CMD_ASK}\n"')

    hint = args.readline_key_send.replace('\\', '')
    self.logger.info(f"Type /help or a question followed by the /ask command (or by pressing "
          f"`{hint}` key).")

    self.file = file
    self.repl = Repl(self, self.logger)
    self.reset()

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

  def _sync2(self, ast:ActorState, cnv:Conversation):
    assert self.cnv_top <= len(cnv.utterances)
    if self.repl.opts is None:
      self.repl.opts = ast.get_desc()
    for i in range(self.cnv_top, len(cnv.utterances)):
      u:Utterance = cnv.utterances[i]
      if u.actor_name != self.name:
        need_eol = False
        buffer_out = []
        streams = {}

        def _sigint(*args, **kwargs):
          for s in streams.values():
            s.interrupt()

        def _printer(s:Stream, token:ContentItem) -> Stream|None:
          nonlocal need_eol
          streams[s.reference] = s
          stream2 = None
          if isinstance(token, bytes):
            need_eol = True
            stdout.buffer.write(token)
            stdout.buffer.flush()
          elif isinstance(token, str):
            need_eol = not token.rstrip(' ').endswith("\n")
            self.repl._print(token, end='')
          elif isinstance(token, Reference):
            # Will dereference a remote reference into a local reference
            token, sn = ast.deref(token)
            if sn.binary and not self.repl.rawbin:
              need_eol = True
              assert sn.suggested_fname is not None, \
                f"Suggested file name for binary stream must be set"
              with open(sn.suggested_fname, 'wb') as f:
                for token2 in sn.gen():
                  f.write(token2)
              self.logger.info("Binary stream has been saved to file")
              buffer_out.append(sn.suggested_fname)
              self.repl._print(f"{sn.suggested_fname}", flush=True)
            else:
              stream2 = sn
          buffer_out.append(token)
          return stream2

        with with_sigint(_sigint):
          traverse_stream(u.contents, _printer)
        self.repl.buffers[OUT] = buffer_out
        if need_eol:
          self.repl._print()
        self.repl._print(flush=True, end='')
      self.cnv_top += 1

  def reset(self):
    self.cnv_top = 0

  def react(self, av:ActorState, cnv:Conversation) -> Utterance:
    # FIMXE: A minor problem here in the paste_mode [1]: interpreter eats the
    # input first, and handles the paste mode after that. It should raise
    # InterpreterPause instead.
    self._sync2(av, cnv)
    normal_parser = ReplParser(self.repl)
    paste_parser = PasteModeReplParser(self.repl)
    parser = normal_parser

    while True:
      eof, pres = self.file.process(parser, prompt=self.repl.readline_prompt)
      if (paste_mode := pres.paste_mode) is not None:
        parser = paste_parser if paste_mode else normal_parser
      if eof:
        print()
        return Utterance.init(
          name=self.name,
          intention=Intention.init(exit_flag=True)
        )
      if (utterance := pres.result) is not None:
        return utterance

  def set_options(self, opt:ActorOptions) -> None:
    pass

  def get_options(self)->ActorOptions:
    return ActorOptions.init()

