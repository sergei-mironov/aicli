from typing import Iterable
from contextlib import contextmanager
from signal import signal, SIGINT, SIGALRM, setitimer, ITIMER_REAL
from os.path import join, isfile, realpath, expanduser, abspath, sep
from glob import glob
from sys import stderr

from .types import Actor


def err(s:str, actor:Actor|None=None)->None:
  print(f"ERROR: {s}", file=stderr)

def info(s:str, actor:Actor|None=None, prefix=True)->None:
  prefix = "INFO: " if prefix else ""
  print(f"{prefix}{s}", file=stderr)

def dbg(s:str, actor:Actor|None=None)->None:
  if actor and actor.opt.verbose>0:
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

def expand_apikey(apikey)->str|None:
  schema,val = apikey
  if schema=="verbatim":
    return val
  elif schema=="file":
    try:
      with open(expanduser(val)) as f:
        return f.read().strip()
    except Exception as err:
      raise ValueError(str(err)) from err
  else:
    raise ValueError(f"Unsupported APIKEY schema '{schema}'")

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

