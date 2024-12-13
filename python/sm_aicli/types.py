from typing import Iterable, Callable
from dataclasses import dataclass
from copy import deepcopy
from enum import Enum

class ConversationException(ValueError):
  pass

# PathStr is a string holding a path to a file
PathStr = str

@dataclass(frozen=True)
class ModelName:
  """ Name of an AI model, containing a model provider name (such as `openai` or `gpt4all`) and a
  model name or path to a file. """
  provider:str
  model:str|PathStr
  alias:str|None=None

  def repr(self)->str:
    model = f":{self.model}" if self.model is not None else "default"
    alias = f"({self.alias})" if self.alias is not None else ""
    return f"{self.provider}{model}{alias}"

@dataclass(frozen=True)
class UserName:
  """ A tag representing a user-facing actor """
  pass

class Modality(Enum):
  """ A primitive mime-type for content """
  Text = 0
  Image = 1

@dataclass
class ActorOptions:
  """ Structure encoding all supported options an actor might accept. Unused options are to be
  ignored with a warning. """
  verbose:int=3
  apikey:str|None = None
  temperature:float|None = None
  num_threads:int|None = None
  prompt:str|None = None
  imgsz:str|None = None
  imgnum:int|None = None
  modality:Modality|None=None
  image_dir:str|None=None
  model_dir:str|None=None

  @staticmethod
  def init():
    return ActorOptions()

# Actor name is either an AI model name or a tag representing a user actor.
ActorName = ModelName | UserName

@dataclass
class ActorView:
  """ Serializable subset of actor options """
  options: dict[ActorName, ActorOptions]

  @staticmethod
  def init():
    return ActorView({})

@dataclass
class Intention:
  """ Intention encodes actions that actors might want to perform in addition to saying an
  utterance """
  actor_next: ActorName|None      # Select next actor
  actor_updates: ActorView|None   # Update the list of actors
  exit_flag:bool                  # Exit the application
  reset_flag:bool                 # Reset the conversation
  dbg_flag:bool                   # Run the Python debugger

  @staticmethod
  def init(actor_next=None, actor_updates=None, exit_flag=False, reset_flag=False,
           dbg_flag=False):
    return Intention(actor_next, actor_updates, exit_flag, reset_flag, dbg_flag)

class Stream:
  """ Stream represents a promise to fetch the content from a remote source of some kind. The
  convention is to call gen() only once for every stream. The returned tokens are also stored in the
  `recording` array. All tokens must be of a same type (str or bytes). """

  def __init__(self, generator, binary:bool=False, suggested_fname:str|None=None):
    self.generator = generator    # Descendant-specific token generator
    self.stop = False             # Interrupt flag
    self.recording = None         # Stream recording
    self.binary = binary          # Type of content (False => str; True => bytes)
    self.suggested_fname = suggested_fname # Suggested filename with extension

  def __deepcopy__(self, memo):
    assert self.generator is None, "Can not call deepcopy on the unreaden stream"
    return deepcopy(self, memo)

  def gen(self):
    """ Iterate over tokens. Should be called once in the object's lifetime. """
    self.stop = False
    self.recording = ""
    try:
      for ch in self.generator:
        if self.stop:
          break
        yield ch
        self.recording += ch
    finally:
      self.generator = None

  def interrupt(self):
    """ Declare that no more tokens are going to be fetched from this stream. """
    self.stop = True

# Utterance content is a list of items, where item is either a string, an array of bytes (for
# pictures), or a stream of thereof. The stream represents a promise to fetch the data from a remote
# source of some kind.
Contents = list[str|bytes|Stream]

@dataclass
class Utterance:
  """ An abstraction over conversation utterances. An utterance has its owner (issuer), a target
  actor, a contents, and an (non-verbal) intention. """
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
  """ A conversation actors, a chain of utterances. The convention is to either add new utterances
  to the end of the list or reset the conversation to the initial (empty) state. """
  utterances:Utterances

  def reset(self):
    """ TODO: redundant? """
    self.utterances = []

  @staticmethod
  def init():
    return Conversation([])


# A well-known JSON `[{'role':'user'|'assistant', 'content':str}]` format, accepted by both OpenAI
# and GPT4All APIs.
SAU = list[dict[str, str]]

@dataclass
class ActorState:
  """ Actor state represent a set of non-serializable resources allocated by conversation
  participants - actors."""
  actors: dict[ActorName, "Actor"]

  def get_view(self) -> ActorView:
    """ For each actor, produce a serializable set of options. """
    return ActorView({n:deepcopy(a.get_options()) for n,a in self.actors.items()})

  @staticmethod
  def init():
    return ActorState({})

class Actor:
  """ A conversation participant, known by name. The descendants track actor resources such as
  remote API authorization tokens or AI models themselves. """
  def __init__(self, name:ActorName, opt:ActorOptions):
    self.name = name
    self.opt = opt

  def react(self, act:ActorView, cnv:Conversation) -> Utterance:
    """ Take a view on participants, and a conversation object, produce a new Utterance to be added
    to the conversation. Actors are allowed to cache the conversation in some actor-specific way.
    """
    raise NotImplementedError()

  def reset(self):
    """ Clear cached conversation data. """
    raise NotImplementedError()

  def set_options(self, opt:ActorOptions)->None:
    """ Set new actor options """
    self.opt = opt

  def get_options(self)->ActorOptions:
    """ Get actor's options """
    return self.opt

