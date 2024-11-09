from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from itertools import cycle

from ..types import (Actor, ActorName, ActorOptions, ActorView, Intention, Conversation,
                     Utterance, UserName, Stream)


class DummyActor(Actor):
  def __init__(self, name:ActorName, opt:ActorOptions):
    super().__init__(name, opt)

  def reset(self):
    pass

  def react(self, act:ActorView, cnv:Conversation) -> Utterance:
    response = [Stream([
      f"I am a dummy actor '{self.name.repr()}'\n",
      f"My api key is '{self.opt.apikey}'\n",
      f"My temperature is '{self.opt.temperature}'\n",
      f"My prompt is '{self.opt.prompt}'\n",
    ])]
    return Utterance.init(self.name, Intention.init(actor_next=UserName()), response)
