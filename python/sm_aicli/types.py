from dataclasses import dataclass
from copy import deepcopy

@dataclass(frozen=True)
class ModelName:
  provider:str
  model:str

  def __repr__(self)->str:
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

  @staticmethod
  def init():
    return ActorOptions()

PathStr = str

ActorName = ModelName | UserName

@dataclass
class Utterance:
  actor_name: ActorName
  contents: str

@dataclass
class Conversation:
  """ A conversation between a user and one or more AI models. """
  utterances:list[Utterance]

  def reset(self):
    """ TODO: redundant? """
    self.utterances = []

  @staticmethod
  def init():
    return Conversation([])


@dataclass
class ActorView:
  options: dict[ActorName, ActorOptions]

  @staticmethod
  def init():
    return ActorView({})


@dataclass
class ActorResponse:
  utterance: Utterance|None
  actor_next: ActorName|None
  actor_updates: ActorView|None
  exit_flag:bool

  @staticmethod
  def init(utterance=None, actor_next=None, actor_updates=None, exit_flag=False):
    return ActorResponse(utterance, actor_next, actor_updates, exit_flag)


@dataclass
class ActorState:
  """ Non-serializable interpreter state. Allocated models, pending options, current model name."""
  actors: dict[ActorName, "Actor"]

  def get_view(self) -> ActorView:
    return ActorView({n:deepcopy(a.get_options()) for n,a in self.actors.items()})

  @staticmethod
  def init(initial:"Actor"):
    return ActorState({initial.name:initial})

class Actor:
  """ Abstraction of model """
  def __init__(self, name:ActorName, opt:ActorOptions):
    self.name = name
    self.opt = opt

  def comment_with_text(self, act:ActorView, cnv:Conversation) -> ActorResponse:
    """ Return a token generator object, responding the message. """
    raise NotImplementedError()

  def comment_with_image(self, act:ActorView, cnv:Conversation) -> ActorResponse:
    """ Return a path to generated image, responding the message. """
    raise NotImplementedError()

  def set_options(self, opt:ActorOptions)->None:
    self.opt = opt

  def get_options(self)->ActorOptions:
    return self.opt

