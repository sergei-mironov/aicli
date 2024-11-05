from typing import Any
from contextlib import contextmanager
from gpt4all import GPT4All
from copy import deepcopy
from os.path import isfile
from os import getcwd
from dataclasses import dataclass

from ..types import (Conversation, Actor, ActorName, ActorView, ActorOptions, Utterance,
                     Intention, ModelName, UserName)
from ..utils import expandpath, info, dbg, find_last_message

def firstfile(paths) -> str|None:
  for p in paths:
    if isfile(p):
      return p
  return None


@dataclass
class GPT4AllUtterance(Utterance):
  actor:Any|None = None
  def interrupt(self):
    self.actor.break_request = True
  def init(name, intention, actor):
    def _gen(self):
      actor.break_request = False
      self.actor = actor
      self.contents = ''
      try:
        for chunk in actor.chunks:
          if actor.break_request:
            break
          self.contents += chunk
          yield chunk
        assert actor.gpt4all._history[-1]["role"] == "assistant"
        del actor.gpt4all._history[-1]
      finally:
        actor.chunks = None
    return GPT4AllUtterance(name, intention, contents=None, gen=_gen)


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
    self.session.__exit__(None, None, None)

  def _sync(self, cnv:Conversation) -> None:
    assert self.cnvtop < len(cnv.utterances)
    history = self.gpt4all._history
    for i in range(self.cnvtop, len(cnv.utterances)):
      u = cnv.utterances[i]
      assert u.contents is not None, "Utterance without contents is not supported"
      role = None
      if u.actor_name == UserName():
        role = "user"
      else:
        role = "assistant"
      assert role is not None
      history.append({"role":role, "content": u.contents})
      self.cnvtop += 1
    dbg(f"gpt4all history: {self.gpt4all._history}", actor=self)

    last_user_message, last_user_message_id = find_last_message(history, "user")
    if last_user_message_id == len(history)-1:
      del history[last_user_message_id]
      dbg(f"actor history: removing very last message {last_user_message_id}", actor=self)
    return last_user_message or ""

  def reset(self):
    dbg("Resetting session", actor=self)
    self.session.__exit__(None, None, None)
    self.session = self.gpt4all.chat_session()
    self.session.__enter__()
    self.cnvtop = 0

  def comment_with_text(self, act:ActorView, cnv:Conversation) -> Utterance:
    assert self.chunks is None, "Re-entering is not allowed"
    last_user_message = self._sync(cnv)
    def _model_callback(*args, **kwargs):
      return not self.break_request
    self.chunks = self.gpt4all.generate(
      last_user_message,
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
    return GPT4AllUtterance.init(self.name, Intention.init(actor_next=UserName()), self)

  def set_options(self, opt:ActorOptions)->None:
    self.opt = deepcopy(opt)
    if opt.num_threads is not None:
      self.gpt4all.model.set_thread_count(opt.num_threads)
    if opt.prompt is not None:
      info("Custom prompt is ignored by this model", actor=self)

