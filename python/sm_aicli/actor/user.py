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
from os.path import expanduser, abspath, sep, join, isfile, isdir, split
from io import StringIO
from pdb import set_trace as ST

from ..types import (Actor, ActorName, ActorOptions, Intention, Utterance,
                     Conversation, ActorView, ModelName, Modality)

from ..utils import (info, err, with_sigint, dbg, cont2strm, version, sys2exitcode, WLState,
                     wraplong)

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

def _mkref(tail):
  return {
    " verbatim:":{"STRING":tail},
    " file:":{"FILE":tail},
    " bfile:":{"FILE":tail},
    " buffer:":{"BUFFER":tail}}

REF = _mkref({})
REF_REF = _mkref(REF)

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
      " apikey":    REF,
      " imgsz":     {" string": {}},
      " temp":      {" FLOAT":  {}, " default": {}},
      " nt":        {" NUMBER": {}, " default": {}},
      " verbosity": {" NUMBER": {}, " default": {}},
    },
    " terminal": {
      " modality": {
        " modality_string": {}
      },
      " rawbin": VBOOL,
      " prompt": {" string": {}},
      " width": {" NUMBER": {}, " default": {}},
    }
  },
  CMD_CP:      REF_REF,
  CMD_APPEND:  REF_REF,
  CMD_CAT:     REF,
  CMD_CLEAR:   REF,
  CMD_SHELL:   REF,
  CMD_CD:      REF
}

SCHEMAS = [str(k).strip().replace(':','') for k in REF.keys()]
PROVIDERS = [str(p).strip().replace(':','') for p in MODEL.keys()]

CMDHELP = {
  CMD_APPEND:  ("REF REF",       "Append a file, a buffer or a constant to a file or to a buffer."),
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
  CMD_VERSION: ("",              "Print version"),
}

GRAMMAR = fr"""
  start: (command | escape | text)? (command | escape | text)*
  text: TEXT
  escape: ESCAPE
  # Commands start with `/`. Use `\/` to process next `/` as a regular text.
  # The commands are:
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
                                         /verbosity/ / +/ (NUMBER | DEF)) | \
                               (/term/ | /terminal/) / +/ (/modality/ / +/ MODALITY | \
                                                           /rawbin/ / +/ BOOL | \
                                                           /prompt/ / +/ string | \
                                                           /width/ / +/ (NUMBER | DEF))) | \
             /\{CMD_CP}/ / +/ ref / +/ ref | \
             /\{CMD_APPEND}/ / +/ ref / +/ ref | \
             /\{CMD_CAT}/ / +/ ref | \
             /\{CMD_CLEAR}/ / +/ ref | \
             /\{CMD_SHELL}/ / +/ ref | \
             /\{CMD_CD}/ / +/ ref | \
             /\{CMD_PASTE}/ / +/ BOOL

  # Strings can start and end with a double-quote. Unquoted strings should not contain spaces.
  string:  "\"" "\"" | "\"" STRING_QUOTED "\"" | STRING_UNQUOTED

  # Model references are strings with the provider prefix
  model_ref: (PROVIDER ":")? string

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
  TEXT.0: /([^#](?!\/))*[^\/#]/s
  NUMBER: /[0-9]+/
  FLOAT: /[0-9]+\.[0-9]*/
  DEF: "default"
  BOOL: {'|'.join(['/'+str(k).strip()+'/' for k in VBOOL.keys()])}
  MODALITY: /img/ | /text/
  %ignore /#[^\n]*/
"""

PARSER = Lark(GRAMMAR, start='start', propagate_positions=True)

no_model_is_active = "No model is active, use /model first"

def as_float(val:Token, default:float|None=None)->float|None:
  assert val.type == 'FLOAT' or str(val) in {"def","default"}, val
  return float(val) if str(val) not in {"def","default"} else default

def as_int(val:Token, default:int|None=None)->int|None:
  assert val.type == 'NUMBER' or str(val) in {"def","default"}, val
  return int(val) if str(val) not in {"def","default"} else default

def as_bool(val:Token):
  assert val.type == 'BOOL', val
  if str(val) in ['true','yes','1','on']:
    return True
  elif str(val) in ['false','no','0','off']:
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

def ref_quote(ref, prefixes):
  for p in [(p+':') for p in prefixes]:
    if ref.startswith(p) and (' ' in ref[len(p):]):
      return f"{schema}\"{ref[len(p):]}\""
  return ref


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
    self.readline_prompt = args.readline_prompt
    self.wlstate = WLState(None)

  def _check_next_actor(self):
    if self.actor_next is None:
      raise RuntimeError(no_model_is_active)

  def _reset(self):
    self.in_echo = 0
    self.buffers[IN] = ""
    self.buffers[OUT] = ""

  def _print(self, s=None, flush=False, end='\n'):
    wraplong((s or '') + end, self.wlstate, lambda s: print(s, end='', flush=True), flush=flush)

  def reset(self):
    old_message = self.buffers[IN]
    self._reset()
    if len(old_message) > 0:
      info("Message buffer is now empty")

  def _finish_echo(self):
    if self.in_echo:
      self._print(flush=True)
    self.in_echo = 0

  def string(self, tree)->str:
    if tree.children:
      assert len(tree.children) == 1, tree
      assert tree.children[0].type in ('STRING_QUOTED','STRING_UNQUOTED'), tree
      return tree.children[0].value
    else:
      return ""

  def ref(self, tree):
    val = self.visit_children(tree)
    return (str(val[0]), val[1]) if len(val) == 2 else (self.ref_schema_default, val[0])

  def model_ref(self, tree):
    val = self.visit_children(tree)
    return (str(val[0]), val[1]) if len(val) == 2 else (val[0], "default")

  def ref_file(self, tree):
    args = self.visit_children(tree)
    val = ref_read(args[2], self.buffers)
    return ("file", val.strip())

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
        contents = [copy(self.buffers[IN])] if len(self.buffers[IN].strip()) > 0 else []
        val = self.visit_children(tree)
        if self.actor_next is None:
          info(f'No model is active, use /model first')
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
      self._print(self.args.help)
      self._print("Command-line grammar:")
      self._print(GRAMMAR)
      self._print("Commands summary:\n")
      self._print('\n'.join([f"  {c:12s} {h[0]:15s} {h[1]}" for c,h in CMDHELP.items()]),
                  flush=True)
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
          info(f"Setting model image size to '{opts[self.actor_next].imgsz}'")
        elif pname == 'verbosity':
          val = as_int(pval)
          opts[self.actor_next].verbose = val
          info(f"Setting actor verbosity to '{val}'")
        else:
          raise ValueError(f"Unknown actor parameter '{pname}'")
      elif section in ['term', 'terminal']:
        if pname == 'modality':
          if str(pval) == 'img':
            mod = Modality.Image
          elif str(pval) == 'text':
            mod = Modality.Text
          else:
            raise ValueError(f"Invalid modality {pval}")
          info(f"Setting terminal expected modality to '{mod}'")
          self.modality = mod
        elif pname == 'rawbin':
          val = as_bool(pval)
          info(f"Setting terminal raw binary mode to '{val}'")
          self.rawbin = val
        elif pname == 'prompt':
          self.readline_prompt = pval
          info(f"Setting terminal prompt to '{self.readline_prompt}'")
        elif pname == 'width':
          self.wlstate.max_width = as_int(pval, None)
          info(f"Setting terminal width to '{self.wlstate.max_width}'")
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
      self._print(val, flush=True)
    elif command == CMD_SHELL:
      self.ref_schema_default = "verbatim"
      args = self.visit_children(tree)
      ref = args[2]
      cmd = ref_read(ref, self.buffers).strip()
      retcode = sys2exitcode(system(cmd))
      info(f"Shell command '{cmd}' exited with code {retcode}")
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
      self._print(version(), flush=True)
    elif command == CMD_PASTE:
      args = self.visit_children(tree)
      val = as_bool(args[2])
      if val:
        info("Entering paste mode. Type '/paste off' to finish.")
      else:
        info("Exiting paste mode.")
      self.paste_mode = val
    else:
      raise ValueError(f"Unknown command: {command}")

  def text(self, tree):
    text = tree.children[0].value
    if self.in_echo:
      if self.in_echo == 1:
        self._print(text.strip(), end='')
        self.in_echo = 2
      else:
        self._print(text, end='')
    else:
      commands = []
      for cmd in list(CMDHELP.keys()):
        if cmd in text:
          commands.append(cmd)
      if commands:
        info(f"Warning: {', '.join(['`'+c+'`' for c in commands])} were parsed as a text")
      self.buffers[IN] += text

  def escape(self, tree):
    text = tree.children[0].value[1:]
    if self.in_echo:
      self._print(text)
    else:
      self.buffers[IN] += text

  def visit(self, tree):
    self.in_echo = 0
    try:
      res = super().visit(tree)
    finally:
      self._finish_echo()
    return res


def reload_history(args):
  if args.readline_history:
    try:
      clear_history()
      read_history_file(args.readline_history)
      info(f"History file loaded")
    except FileNotFoundError:
      info(f"History file not loaded")
  else:
    info(f"History file is not used")

def read_configs(args, rcnames:list[str])->list[str]:
  acc = []
  current_dir = abspath(getcwd())
  path_parts = current_dir.split(sep)
  for depth in range(2, len(path_parts) + 1):
    directory = sep.join(path_parts[:depth])
    for fn in rcnames:
      candidate_file = join(directory, fn)
      if isfile(candidate_file):
        with open(candidate_file, 'r') as file:
          info(f"Reading {candidate_file}")
          for line in file.readlines():
            info(line.strip())
            acc.append(line.strip())
  return acc

class UserActor(Actor):

  def __init__(self,
               name:ActorName,
               opt:ActorOptions,
               args:Any,
               prefix_stream:str|None = None):
    super().__init__(name, opt)

    if args.readline_history:
      args.readline_history = abspath(expanduser(args.readline_history))

    header = StringIO()
    rcnames = environ.get('AICLI_RC', args.rc)
    if rcnames is not None and len(rcnames)>0 and rcnames!='none':
      for line in read_configs(args, rcnames.split(',')):
        header.write(line+'\n')
    else:
      info("Skipping configuration files")
    if args.model is not None:
      header.write(f"/model {ref_quote(args.model, PROVIDERS)}\n")
    if args.model_apikey is not None:
      header.write(f"/set model apikey {ref_quote(args.model_apikey, SCHEMAS)}\n")

    for file in args.filenames:
      with open(file) as f:
        info(f"Reading {file}")
        header.write(f.read())

    set_completer_delims('')
    set_completer(self._complete)
    parse_and_bind('tab: complete')
    parse_and_bind(f'"{args.readline_key_send}": "{CMD_ASK}\n"')
    hint = args.readline_key_send.replace('\\', '')
    info(f"Type /help or a question followed by the /ask command (or by pressing "
          f"`{hint}` key).")

    reload_history(args)

    self.stream = header.getvalue()
    self.args = args
    self.repl = Repl(name, args)
    self.batch_mode = len(args.filenames) > 0
    self.reset()

  def _complete(self, text:str, state:int) -> str|None:
    """ `text` is the text to complete, `state` is an increasing number.
    Function returns the completion text or None if no completions exist. """
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
        for cont in u.contents:
          s = cont2strm(cont)
          def _handler(*args, **kwargs):
            s.interrupt()
          with with_sigint(_handler):
            self.repl.buffers[OUT] = None
            if s.binary and not self.repl.rawbin:
              assert s.suggested_fname is not None, \
                f"Suggested file name for binary stream must be set"
              with open(s.suggested_fname, 'wb') as f:
                for token in s.gen():
                  f.write(token)
              info(f"Binary file has been saved to '{s.suggested_fname}'")
              # cmd = f"{CMD_CP} \"bfile:{s.suggested_fname}\" \"buffer:out\""
              # print(cmd, flush=True)
              # self.stream = cmd + self.stream
              self.repl._print(f"{s.suggested_fname}\n", flush=True)
              self.repl.buffers[OUT] = s.suggested_fname
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
                if self.repl.buffers[OUT] is None:
                  self.repl.buffers[OUT] = b'' if isinstance(token, bytes) else ''
                self.repl.buffers[OUT] += token
        if need_eol:
          self.repl._print()
        self.repl._print(flush=True, end='')
      self.cnv_top += 1

  def reset(self):
    self.cnv_top = 0

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
              self.stream = input(self.repl.readline_prompt) + '\n'
          tree = PARSER.parse(self.stream)
          dbg(tree, self)
          self.repl.visit(tree)
          while self.repl.paste_mode: # [1]
            line = input('P>')
            if line.strip() == '/paste off':
              self.repl.paste_mode = False
            else:
              self.repl.buffers[IN] += line + '\n'
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
