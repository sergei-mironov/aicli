from contextlib import contextmanager
from signal import signal, SIGINT, SIGALRM, setitimer, ITIMER_REAL
from os.path import join, isfile, realpath, expanduser, abspath, sep
from glob import glob
from sys import stderr

from .types import Actor


def err(s:str, actor:Actor|None=None)->None:
  print(f"ERROR: {s}", file=stderr)

def info(s:str, actor:Actor|None=None)->None:
  print(f"INFO: {s}", file=stderr)

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


def expandpath(refdir, path)->list[str]:
  for p in [path] + ([join(refdir, path)] if refdir else []):
    for match in glob(expanduser(p)):
      yield realpath(match)
