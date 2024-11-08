from typing import Iterable, Callable
from dataclasses import dataclass
from copy import deepcopy
from enum import Enum

class ConversationException(ValueError):
  pass

@dataclass(frozen=True)
class ModelName:
  provider:str
  model:str

  def repr(self)->str:
    return f"{self.provider}:{self.model}"

@dataclass(frozen=True)
class UserName:
  pass

@dataclass
class ActorOptions:
  """ Model options """
  verbose:int=0
  apikey:str|None = None
  temperature:float|None = None
  num_threads:int|None = None
  prompt:str|None = None
  imgsz:str|None = None

  @staticmethod
  def init():
    return ActorOptions()

PathStr = str

ActorName = ModelName | UserName

@dataclass
class ActorView:
  options: dict[ActorName, ActorOptions]

  @staticmethod
  def init():
    return ActorView({})

class Modality(Enum):
  Text = 0
  Image = 1

@dataclass
class Intention:
  actor_next: ActorName|None
  actor_updates: ActorView|None
  exit_flag:bool
  reset_flag:bool
  dbg_flag:bool
  modality:Modality=Modality.Text

  @staticmethod
  def init(actor_next=None, actor_updates=None, exit_flag=False, reset_flag=False,
           dbg_flag=False, modality=Modality.Text):
    return Intention(actor_next, actor_updates, exit_flag, reset_flag, dbg_flag,
                         modality=modality)

class Stream:
  def __init__(self, generator, binary=False, suggested_fname:str|None=None):
    self.generator = generator
    self.stop = False
    self.recording = None
    self.binary = binary
    self.suggested_fname = suggested_fname

  def gen(self):
    self.stop = False
    for ch in self.generator:
      if self.stop:
        break
      yield ch
      if self.recording is None:
        self.recording = ch
      else:
        self.recording += ch

  def interrupt(self):
    self.stop = True

Contents = list[str|bytes|Stream]

@dataclass
class Utterance:
  actor_name: ActorName
  intention: Intention
  contents: Contents
  def init(name, intention, contents:Contents|None = None):
    assert contents is None or isinstance(contents, list), contents
    return Utterance(name, intention, contents or [])
  def is_empty(ut):
    return len(ut.contents)==0

Utterances = list[Utterance]
UtteranceId = int
UID = UtteranceId

@dataclass
class Conversation:
  """ A conversation between a user and one or more AI models. """
  utterances:Utterances

  def reset(self):
    """ TODO: redundant? """
    self.utterances = []

  @staticmethod
  def init():
    return Conversation([])


# Well-known [ {'role':'user'|'assistant', 'content':str} ]
SAU = list[dict[str, str]]

@dataclass
class ActorState:
  """ Non-serializable interpreter state. Allocated models, pending options, current model name."""
  actors: dict[ActorName, "Actor"]

  def get_view(self) -> ActorView:
    return ActorView({n:deepcopy(a.get_options()) for n,a in self.actors.items()})

  @staticmethod
  def init():
    return ActorState({})

class Actor:
  """ Abstraction of actor """
  def __init__(self, name:ActorName, opt:ActorOptions):
    self.name = name
    self.opt = opt

  def react(self, act:ActorView, cnv:Conversation) -> Utterance:
    """ Return a token generator object, responding the message. """
    raise NotImplementedError()

  def reset(self):
    """ Resets cached conversation """
    raise NotImplementedError()

  def set_options(self, opt:ActorOptions)->None:
    self.opt = opt

  def get_options(self)->ActorOptions:
    return self.opt

