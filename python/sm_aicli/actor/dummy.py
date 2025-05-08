from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from itertools import cycle
from typing import Any

from ..types import (Actor, ActorName, ActorOptions, ActorView, Intention, Conversation,
                     Utterance, UserName, Stream, File, Parser)

from .user import CMD_ASK


class DummyReplayParser(Parser):
  def parse(self, chunk:str) -> tuple[str,Any]:
    # from pdb import set_trace; set_trace()
    try:
      index = chunk.index(CMD_ASK)
      return chunk[index+len(CMD_ASK):], chunk[:index]
    except ValueError:
      return '', chunk


class DummyActor(Actor):
  def __init__(self, name:ActorName, opt:ActorOptions, file:File):
    super().__init__(name, opt)
    self.file = file

  def reset(self):
    pass

  def react(self, act:ActorView, cnv:Conversation) -> Utterance:
    if not self.file.would_block():
      _,replay = self.file.process(DummyReplayParser(),'')
      response = [replay]
    else:
      response = [Stream([
        f"I am a dummy actor '{self.name.repr()}'\n",
        f"My api key is '{self.opt.apikey}'\n",
        f"My temperature is '{self.opt.temperature}'\n",
        f"My prompt is '{self.opt.prompt}'\n",
      ])]
    return Utterance.init(self.name, Intention.init(actor_next=UserName()), response)
