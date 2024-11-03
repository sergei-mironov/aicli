from contextlib import contextmanager
from signal import signal, SIGINT, SIGALRM, setitimer, ITIMER_REAL
from os.path import join, isfile, realpath, expanduser, abspath, sep

def print_help():
  print(f"Commands: {' '.join(COMMANDS)}")

def print_aux(s:str)->None:
  print(f"INFO: {s}")

def print_aux_err(s:str)->None:
  print(f"ERROR: {s}")


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
