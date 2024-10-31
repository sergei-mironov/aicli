from dataclasses import dataclass

from .model.base import Model, ModelName, Options

@dataclass
class ModelName:
  provider:str
  model:str

@dataclass
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
class ActorRequest:
  """ Request from an actor to change other actors' settings """
  next_actor: ActorName|None
  update_list: dict[ActorName, ActorOptions]
  terminate:bool

  @staticmethod
  def init():
    return ActorRequest(None, {}, False)


class Actor:
  """ Abstraction of model """
  def __init__(self, name:ActorName, opt:ActorOptions):
    self.name = name
    self.opt = opt

  def comment_with_text(self, cnv:Conversation) -> tuple[Utterance|None, ActorRequest|None]:
    """ Return a token generator object, responding the message. """
    raise NotImplementedError()

  def comment_with_image(self, cnv:Conversation) -> tuple[Utterance|None, ActorRequest|None]:
    """ Return a path to generated image, responding the message. """
    raise NotImplementedError()

  def set_options(self, opt:ActorOptions)->None:
    selt.opt = opt

  def get_options(self)->ActorOptions:
    return self.opt


@dataclass
class ActorState:
  """ Non-serializable interpreter state. Allocated models, pending options, current model name."""
  actors: dict[ActorName, Model]

  @staticmethod
  def init(initial:Actor):
    return ConversationState({initial.name:initial})

