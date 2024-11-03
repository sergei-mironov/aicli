from typing import Any
from contextlib import contextmanager
from gpt4all import GPT4All
from copy import deepcopy
from os.path import isfile
from os import getcwd
from dataclasses import dataclass

from ..types import (Conversation, Actor, ActorName, ActorView, ActorOptions, Utterance,
                     ActorResponse, ModelName, UserName)
from ..utils import expandpath

def firstfile(paths) -> str|None:
  for p in paths:
    if isfile(p):
      return p
  return None


@dataclass
class GPT4AllUtterance(Utterance):
  actor:"GPT4AllActor"
  def interrupt(self):
    self.actor.break_request = True
  def gen(self):
    self.actor.break_request = False
    self.contents = ''
    try:
      for chunk in self.actor.chunks:
        if self.actor.break_request:
          break
        yield chunk
        self.contents += chunk
      assert self.actor.gpt4all._history[-1]["role"] == "assistant"
      del self.actor.gpt4all._history[-1]
    finally:
      self.actor.chunks = None


class GPT4AllActor(Actor):
  temperature_def = 0.9

  def __init__(self, name:ActorName, opt:ActorOptions, refdir:str|None):
    assert isinstance(name, ModelName)
    assert name.provider == "gpt4all"
    self.name = deepcopy(name)
    path_or_name = firstfile(expandpath(refdir or getcwd(), name.model)) or name.model
    self.gpt4all = GPT4All(path_or_name)
    self.session = self.gpt4all.chat_session()
    self.session.__enter__()
    self.break_request = False
    self.cnvtop = 0
    self.chunks = None
    self.set_options(opt)

  def __del__(self):
    self.session.__exit__()

  def _sync(self, cnv:Conversation) -> list:
    history = []
    for i in range(self.cnvtop, len(cnv.utterances)):
      u = cnv.utterances[i]
      assert isinstance(u.contents, str)
      role = "user" if u.actor_name == UserName() else "assistant"
      history.append({"role":role, "content": u.contents})
      self.cnvtop += 1
    return history

  def comment_with_text(self, act:ActorView, cnv:Conversation) -> ActorResponse:
    assert self.chunks is None, "Re-entering is not allowed"
    self.gpt4all._history.extend(self._sync(cnv))
    assert self.gpt4all._history[-1]['role'] == 'user'
    user_message = self.gpt4all._history[-1]['content']

    def _model_callback(*args, **kwargs):
      return not self.break_request
    self.chunks = self.gpt4all.generate(
      user_message,
      max_tokens=200,
      temp=self.opt.temperature or self.temperature_def,
      top_k=40,
      top_p=0.9,
      min_p=0.0,
      repeat_penalty=1.1,
      repeat_last_n=64,
      n_batch=9,
      streaming=True,
      callback=_model_callback,
    )

    return ActorResponse.init(
      actor_next=UserName(),
      utterance=GPT4AllUtterance(self.name, None, self)
    )

  def set_options(self, opt:ActorOptions)->None:
    self.opt = deepcopy(opt)
    if opt.num_threads is not None:
      self.gpt4all.model.set_thread_count(opt.num_threads)

