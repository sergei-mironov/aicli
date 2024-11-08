from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from itertools import cycle

from ..types import (Actor, ActorName, ActorOptions, ActorView, Intention, Conversation,
                     Utterance, UserName, Stream)


class DummyActor(Actor):
  def __init__(self, name:ActorName, opt:ActorOptions):
    super().__init__(name, opt)
    apikey = self.opt.apikey if self.opt.apikey else "<no-api-key>"
    print(f"Dummy actor '{self.name.repr()}' apikey '{apikey}'")

  def reset(self):
    pass

  def react(self, act:ActorView, cnv:Conversation) -> Utterance:
    return Utterance.init(self.name, Intention.init(actor_next=UserName()), [Stream(['dummy']*10)])
