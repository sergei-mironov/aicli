from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from itertools import cycle
from typing import Any

from ..types import (Actor, ActorName, ActorOptions, ActorState, Intention, Conversation,
                     Utterance, UserName, File, Parser)
from ..utils import read_until_pattern, cont2str, IterableStream

from .user import CMD_ANS


class DummyActor(Actor):
  def __init__(self, name:ActorName, opt:ActorOptions, file:File):
    super().__init__(name, opt)
    self.file = file

  def reset(self):
    pass

  def react(self, act:ActorState, cnv:Conversation) -> Utterance:
    if self.opt.replay:
      response = read_until_pattern(self.file, CMD_ANS, '(DUMMY)>>> ')
    else:
      response = [IterableStream([
        f"You said:\n```\n",
        cont2str(cnv.utterances[-1].contents,False).strip(),
        f"\n```\n",
        f"I say:\n"
        f"I am a dummy actor '{self.name.repr()}'\n",
        f"My api key is '{self.opt.apikey}'\n",
        f"My temperature is '{self.opt.temperature}'\n",
        f"My prompt is '{self.opt.prompt}'\n",
      ])]
    return Utterance.init(self.name, Intention.init(actor_next=UserName()), response)
