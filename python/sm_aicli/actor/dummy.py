from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from itertools import cycle

from ..types import (Actor, ActorName, ActorOptions, ActorView, ActorResponse, Conversation,
                     Utterance, UserName)

class DummyActor(Actor):

  def __init__(self, name:ActorName, opt:ActorOptions):
    super().__init__(name, opt)
    print(f"Dummy actor '{self.name}' apikey '{self.opt.apikey}'")

  def comment_with_text(self, act:ActorView, cnv:Conversation) -> ActorResponse:
    return ActorResponse.init(utterance=Utterance(self.name, "dummy"), actor_next=UserName())
