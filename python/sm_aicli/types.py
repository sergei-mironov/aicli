from typing import Any, Iterable, Callable
from dataclasses import dataclass
from copy import deepcopy
from enum import Enum
from contextlib import contextmanager
from traceback import print_exc
from abc import ABC, abstractmethod

class ConversationException(ValueError):
  pass

class QuotedString(str):
  pass

class UnquotedString(str):
  pass

# PathStr is a string holding a path to a file
PathStr = str


class Parser:
  """ A Stateful text stream parser """
  def parse(self, chunk:str) -> tuple[str,Any]:
    """ Parse a chunk of input stream, return the unparsed stream and a parser-specific state """
    raise NotImplementedError()


class File:
  """ Input file, e.g. stdin. """
  def process(self, parser:Parser, prompt:str) -> tuple[bool, Any]:
    """ Read and parse the contents using a Parser. Unparsed stream should be
    placed into a buffer and attempted on the next call. """
    raise NotImplementedError()


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
  """ Structure that encodes all the supported options actors might accept.
  Unused options are to be ignored with a warning. """
  verbose:int=2
  apikey:str|None = None
  temperature:float|None = None
  num_threads:int|None = None
  prompt:str|None = None
  imgsz:str|None = None
  imgnum:int|None = None
  modality:Modality|None=None
  image_dir:str|None=None
  model_dir:str|None=None
  seed:int|None=None
  replay:bool=False            # Read replies from a file instead of from models
  proxy:str|None=None          # Proxy string to use,
                               # For OpenAI see https://www.python-httpx.org/advanced/proxies/

  @staticmethod
  def init():
    return ActorOptions()

# Actor name is either an AI model name or a tag representing a user actor.
ActorName = ModelName | UserName

ActorDesc = dict[ActorName, ActorOptions]

@dataclass
class Intention:
  """ Intention encodes actions that an actor might want to perform in addition to saying an
  utterance. """
  actor_next: ActorName|None      # Select next actor
  actor_updates: ActorDesc|None   # Update to the list of actors
  exit_flag:bool                  # Exit the application
  reset_flag:bool                 # Reset the conversation
  dbg_flag:bool                   # Run the Python debugger

  @staticmethod
  def init(actor_next=None, actor_updates=None, exit_flag=False, reset_flag=False,
           dbg_flag=False):
    return Intention(actor_next, actor_updates, exit_flag, reset_flag, dbg_flag)


@dataclass(frozen=True)
class Reference:
  pass

@dataclass(frozen=True)
class RemoteReference(Reference):
  mimetype: str
  url: str

@dataclass(frozen=True)
class LocalReference(Reference):
  mimetype: str
  path: str

@dataclass(frozen=True)
class ActorReference(Reference):
  actor_name: ActorName|None = None

type ContentItem = str | bytes | Reference

type LocalContent = list[ContentItem]

class Stream(ABC):
  """ Stream represents a promise to fetch the content from a remote source of some kind. The
  convention is to call gen() only once for every stream. The returned tokens are also stored in the
  `recording` array. All tokens must be of a same type (str or bytes). """
  def __init__(self, reference:Reference=Reference()):
    self.binary: bool|None = None           # Binary flag, None means Unknown
    self.stop:bool = False                  # Interrupt flag
    self.recording:LocalContent|None = None # Stream recording
    self.reference:Reference = reference

  @abstractmethod
  def gen(self) -> Iterable[ContentItem]:
    """ Yield next ContentItem. """
    ...

  def interrupt(self) -> None:
    """ Makes `gen` exit. """
    self.stop = True


# Utterance content is a list of items, where an item is either a string, an array of bytes (for
# pictures), or a stream of thereof. The stream represents a promise to fetch the data from a remote
# source of some kind.
# FIXME: Switch to `ContentItem` and co.
# Contents = list[str|bytes|Stream]
type Contents = Stream

@dataclass
class Utterance:
  """ An abstraction over conversation utterances. An utterance has its owner (issuer), a target
  actor, a contents, and an (non-verbal) intention. A conversation is setializable provided that
  Contents contains no unread Streams."""
  actor_name: ActorName
  intention: Intention
  contents: Stream|None
  def init(name, intention, contents:Stream|None = None):
    assert contents is None or isinstance(contents, Stream), \
      f"Utterance requires Stream contents or None, got {contents}"
    return Utterance(name, intention, contents)
  def is_empty(ut):
    return ut.contents is None

Utterances = list[Utterance]
UtteranceId = int
UID = UtteranceId

@dataclass
class Conversation:
  """ A conversation of actors, a chain of utterances. The convention is to
  either add new utterances to the end of the list or reset the conversation to
  the initial (empty) state. """
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


class Dereferencer(ABC):
  @abstractmethod
  def deref(self, Reference) -> tuple[Reference, Stream]:
    raise NotImplementedError()

class ActorViewer(ABC):
  @abstractmethod
  def get_desc(self) -> ActorDesc:
    raise NotImplementedError()

class ActorState(ActorViewer, Dereferencer):
  pass

class Actor:
  """ A conversation participant, known by name. The descendants track actor resources such as
  remote API authorization tokens or AI models themselves. """
  def __init__(self, name:ActorName, opt:ActorOptions):
    self.name = name
    self.opt = opt

  def react(self, act:ActorState, cnv:Conversation) -> Utterance:
    """ Take a view on participants, and a conversation object, produce a new Utterance to be added
    to the conversation. Actors are allowed to cache the conversation in some actor-specific way.
    """
    raise NotImplementedError()

  def reset(self):
    """ Clear cached conversation data. """
    raise NotImplementedError()

  def set_options(self, opt:ActorOptions)->None:
    """ Set new actor options.
    FIXME: remove? Use react() to change options """
    self.opt = opt

  def get_options(self)->ActorOptions:
    """ Get actor's options.
    FIXME: Remove? There should be no need to ask clients for options? """
    return self.opt


class Logger:
  def __init__(self, actor:Actor):
    self.actor = actor
  def err(self, s:str):
    raise NotImplementedError()
  def info(self, s:str) -> None:
    raise NotImplementedError()
  def warn(self, s:str) -> None:
    raise NotImplementedError()
  def dbg(self, s:str):
    raise NotImplementedError()
