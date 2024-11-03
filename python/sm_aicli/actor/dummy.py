from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from itertools import cycle

from ..types import (Actor, ActorName, ActorOptions, ActorView, ActorResponse, Conversation,
                     Utterance, UserName)

class DummyUtterance(Utterance):
  stop:bool = False
  def interrupt(self):
    self.stop = True
  def gen(self):
    self.stop = False
    self.contents = ''
    for i in range(10):
      if self.stop:
        break
      token = "dummy\n"
      self.contents += token
      yield token

class DummyActor(Actor):

  def __init__(self, name:ActorName, opt:ActorOptions):
    super().__init__(name, opt)
    print(f"Dummy actor '{self.name.repr()}' apikey '{self.opt.apikey}'")

  def comment_with_text(self, act:ActorView, cnv:Conversation) -> ActorResponse:
    return ActorResponse.init(utterance=DummyUtterance(self.name, None),
                              actor_next=UserName())
