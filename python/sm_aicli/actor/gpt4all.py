from typing import Any
from contextlib import contextmanager
from gpt4all import GPT4All
from copy import deepcopy
from os.path import isfile
from dataclasses import dataclass
from collections import OrderedDict

from ..types import (Conversation, Actor, ActorName, ActorState, ActorOptions, Utterance,
                     Intention, ModelName, UserName, SAU, Stream)
from ..utils import (ConsoleLogger, expandpath, find_last_message, uts_lastfullref, uts_2sau, firstfile)


class GPT4AllStream(Stream):
  def __init__(self, actor):
    super().__init__(actor.chunks)
    self.actor = actor
  def gen(self):
    try:
      yield from super().gen()
      assert self.actor.gpt4all._history[-1]["role"] == "assistant"
      del self.actor.gpt4all._history[-1]
    finally:
      self.actor.chunks = None


class GPT4AllActor(Actor):
  temperature_def = 0.9

  def __init__(self, name:ActorName, opt:ActorOptions):
    assert isinstance(name, ModelName)
    assert name.provider == "gpt4all"
    self.name = deepcopy(name)
    model_dir = opt.model_dir or "."
    path_or_name = firstfile(expandpath(model_dir, name.model)) or name.model
    self.gpt4all = GPT4All(path_or_name)
    self.session = self.gpt4all.chat_session()
    self.session.__enter__()
    self.break_request = False
    self.cache = OrderedDict()
    self.chunks = None
    self.logger = ConsoleLogger(self)
    self.set_options(opt)

  def __del__(self):
    self.session.__exit__(None, None, None)

  def reset(self):
    self.logger.dbg("Resetting session")
    self.session.__exit__(None, None, None)
    self.session = self.gpt4all.chat_session()
    self.session.__enter__()
    self.cache = OrderedDict()

  def _sync(self, cnv:Conversation) -> tuple[SAU, str]:
    uid = uts_lastfullref(cnv.utterances, self.name)
    if uid is None:
      raise ConversationException("No context")
    sau = uts_2sau(cnv.utterances[:uid+1],
                   {UserName():"user"},
                   "assistant",
                   self.opt.prompt or '',
                   self.cache)
    if len(self.cache)>5:
      self.cache.popitem(last=False)
    assert len(sau)>0, f"{sau}"
    assert sau[-1]['role'] == 'user', f"{sau}"
    return sau[:-1], sau[-1]['content']

  def react(self, act:ActorState, cnv:Conversation) -> Utterance:
    assert self.chunks is None, "Re-entering is not allowed"
    sau, prompt = self._sync(cnv)
    self.logger.dbg(f"sau: {sau}")
    self.logger.dbg(f"prompt: {prompt}")
    self.gpt4all._history = sau
    def _model_callback(*args, **kwargs):
      return not self.break_request
    if self.opt.seed is not None:
      warn(f"gpt4all actor does not support seed", actor=self)
    self.chunks = self.gpt4all.generate(
      prompt,
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
    return Utterance.init(self.name, Intention.init(actor_next=UserName()), [GPT4AllStream(self)])

  def set_options(self, opt:ActorOptions)->None:
    self.opt = deepcopy(opt)
    if opt.num_threads is not None:
      self.gpt4all.model.set_thread_count(opt.num_threads)

