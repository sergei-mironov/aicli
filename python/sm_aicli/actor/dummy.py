from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from itertools import cycle

from ..types import (Actor, ActorName, ActorOptions, ActorView, Intention, Conversation,
                     Utterance, UserName)

class DummyUtterance(Utterance):
  stop:bool = False
  def interrupt(self):
    self.stop = True
  def init(name, intention):
    def _gen(self):
      self.stop = False
      self.contents = ''
      for i in range(10):
        if self.stop:
          break
        token = "dummy\n"
        self.contents += token
        yield token
    return DummyUtterance(name, intention, None, _gen)

class DummyActor(Actor):

  def __init__(self, name:ActorName, opt:ActorOptions):
    super().__init__(name, opt)
    print(f"Dummy actor '{self.name.repr()}' apikey '{self.opt.apikey}'")

  def reset(self):
    pass

  def comment_with_text(self, act:ActorView, cnv:Conversation) -> Utterance:
    return DummyUtterance.init(self.name, Intention.init(actor_next=UserName()))
