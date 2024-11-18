from typing import Iterable, Callable
from dataclasses import dataclass
from contextlib import contextmanager
from signal import signal, SIGINT, SIGALRM, setitimer, ITIMER_REAL
from os.path import join, isfile, realpath, expanduser, abspath, sep
from glob import glob
from sys import stderr, platform, maxsize
from collections import OrderedDict
from subprocess import check_output, DEVNULL
from os import environ, makedirs, system
from hashlib import sha256
from textwrap import dedent
from pdb import set_trace as ST

from .types import (Actor, Conversation, UID, Utterance, Utterances, SAU, ActorName, Contents,
                    Stream)

REVISION:str|None
try:
  REVISION=environ["AICLI_REVISION"]
except Exception:
  try:
    REVISION=check_output(['git', 'rev-parse', 'HEAD'],
                          cwd=environ['AICLI_ROOT'],
                          stderr=DEVNULL).decode().strip()
  except Exception:
    try:
      from .revision import REVISION as __rv__
      REVISION = __rv__
    except ImportError:
      REVISION = None

VERSION:str|None
try:
  from subprocess import check_output, DEVNULL
  VERSION=check_output(['python3', 'setup.py', '--version'],
                       cwd=environ['AICLI_ROOT'],
                       stderr=DEVNULL).decode().strip()
except Exception:
  try:
    from .revision import VERSION as __ver__
    VERSION = __ver__
  except ImportError:
    VERSION = None


def err(s:str, actor:Actor)->None:
  if actor and actor.opt.verbose > 0:
    print(f"ERROR: {s}", file=stderr)

def warn(s:str, actor:Actor)->None:
  if actor and actor.opt.verbose > 1:
    print(f"WARNING: {s}", file=stderr)

def info(s:str, actor:Actor, prefix=True)->None:
  if actor and actor.opt.verbose > 2:
    prefix = "INFO: " if prefix else ""
    print(f"{prefix}{s}", file=stderr)

def dbg(s:str, actor:Actor)->None:
  if actor and actor.opt.verbose > 3:
    print(f"DEBUG: {s}", file=stderr)


@contextmanager
def with_sigint(_handler):
  """ FIME: Not a very correct singal handler. One also needs to mask signals during switching
  handlers """
  prev=signal(SIGINT,_handler)
  try:
    yield
  finally:
    signal(SIGINT,prev)

def onematch(gen:Iterable[str])->str:
  res = list(gen)
  if len(res)!=1:
    raise ValueError(f"Expected exactly one match, got '{res}'")
  return res[0]

def expanddir(path)->list[str]:
  for match in glob(expanduser(path)):
    yield realpath(match)

def expandpath(refdir, path)->list[str]:
  for p in [path] + ([join(refdir, path)] if refdir else []):
    for match in glob(expanduser(p)):
      yield realpath(match)


def find_last_message(messages:list[dict[str,str]], role:str) -> tuple[str|None,int|None]:
  """ Find last message in the list of messages, return its contents and list index """
  last_message = None
  last_message_id = None
  for i in reversed(range(0, len(messages))):
    if messages[i]['role'] == role:
      last_message = messages[i]['content']
      last_message_id = i
      break
  return last_message, last_message_id


def uts_lastref(uts:Utterances, referree:ActorName) -> UID|None:
  ul = len(uts)
  if ul == 0:
    return None
  uid:UID|None = None
  for i in reversed(range(0, ul)):
    ut = uts[i]
    if ut.intention.actor_next == referree:
      uid = i
      break
  return uid

def uts_lastfull(uts:Utterances, owner:ActorName) -> UID|None:
  uid = None
  for i in reversed(range(0, len(uts))):
    ut = uts[i]
    if ut.actor_name == owner and not ut.is_empty():
      uid = i
      break
  return uid

def uts_lastfullref(uts:Utterances, referree:ActorName) -> UID|None:
  uid = uts_lastref(uts, referree)
  if uid is not None and uts[uid].is_empty():
    uid = uts_lastfull(uts, uts[uid].actor_name)
  return uid

def uts_2sau(
  uts:Utterances,
  names:dict[ActorName, str],
  default_name:str|None = None,
  system_prompt:str|None = None,
  cache:dict[hash,SAU]|None = None
) -> SAU:
  def _cachekey(i):
    return tuple([i, system_prompt, *tuple(names.items())])
  racc:SAU = []
  for i in reversed(range(0, len(uts))):
    if cache is not None:
      cache_key = _cachekey(i)
      cached = cache.get(cache_key)
      if cached is not None:
        return cached + list(reversed(racc))
    ut:Utterance = uts[i]
    name = names.get(ut.actor_name, default_name)
    # assert name in ['user','assistant'], f"Unknown SAU name {name}"
    racc.append({'role':name, 'content':cont2str(ut.contents)})
  racc.append({'role':'system', 'content':system_prompt or ''})
  acc = list(reversed(racc))
  if cache is not None:
    cache[_cachekey(len(uts)-1)] = acc
  return acc

def ensure_quoted(s:str)->str:
  if not (len(s)>0 and s[0]=='"'):
    s = '"' + s
  if not (len(s)>0 and s[-1]=='"'):
    s = s + '"'
  return s

def cont2strm(c:str|bytes|Stream, allow_bytes=True) -> Stream:
  if isinstance(c,str):
    s = Stream([c])
  elif isinstance(c, bytes):
    if allow_bytes:
      s = Stream([c])
    else:
      s = Stream(["<binary chunk>"])
  elif isinstance(c, Stream):
    s = Stream([c.recording]) if c.recording is not None else c
  else:
    assert False, f"Invalid content chunk type {type(c)}"
  return s


def cont2str(cs:Contents, allow_bytes=True)->str|bytes:
  assert isinstance(cs, list), cs
  acc:str|bytes|None = None
  for c in cs:
    for token in cont2strm(c, allow_bytes=allow_bytes).gen():
      acc = token if acc is None else (acc + token)
  return acc or ''

def firstfile(paths) -> str|None:
  for p in paths:
    if isfile(p):
      return p
  return None

def sys2exitcode(ret):
  if platform.startswith("win"):
    return ret
  else: # Linux, etc
    from os import WEXITSTATUS
    return WEXITSTATUS(ret)

def version():
  ver = VERSION
  rev = f"+g{REVISION[:7]}" if REVISION else ""
  return f"{ver}{rev}"

# def words_with_spaces(text):
#   """ Return words with leading spaces """
#   word = ''
#   for char in text:
#     if char.isspace():
#       if word:
#         yield word
#         word = ''
#       word += char
#     else:
#       word += char
#   if word and any((not c.isspace()) for c in word):
#     yield word

@dataclass
class WLState:
  max_width:int|None = None # maximum allowed width
  current_length:int = 0 # length of the current line
  mode:int = 0
  buf:str = ''
  keepspases:bool = False

def wraplong(text:str, state:WLState, printer:Callable, flush:bool=False):
  maxwidth = state.max_width or maxsize
  assert maxwidth >= 1
  spaces, chars, mode, buf = 0, 1, state.mode, state.buf
  keepspases = state.keepspases

  def _newline(ks=False):
    nonlocal keepspases
    printer('\n')
    state.current_length = 0
    keepspases = ks

  def _flushbuf():
    nonlocal buf
    printer(buf)
    state.current_length += len(buf)
    buf = ''

  for char in text:
    if char == '\n':
      if mode == chars:
        if state.current_length + len(buf) >= maxwidth:
          _newline()
        _flushbuf()
        _newline(True)
      elif mode == spaces:
        _newline(True)
        buf = ''
      # mode = chars
    elif char == ' ':
      if mode == chars:
        if state.current_length + len(buf) >= maxwidth:
          _newline()
        _flushbuf()
        if state.current_length >= maxwidth:
          _newline()
      buf += char
      mode = spaces
    else:
      if mode == spaces:
        if state.current_length == 0:
          if not keepspases:
            buf = ''
        else:
          if state.current_length + len(buf) + 1 >= maxwidth:
            _newline()
            buf = ''
          else:
            _flushbuf()
      buf += char
      mode = chars

  if flush:
    if mode == chars:
      if state.current_length + len(buf) >= maxwidth:
        _newline()
      _flushbuf()
      if state.current_length >= maxwidth:
        _newline()
    elif mode == spaces:
      if state.current_length + len(buf) >= maxwidth:
        _newline()
      else:
        _flushbuf()
    mode, buf = chars, ''
  state.mode, state.buf, state.keepspases = mode, buf, keepspases



