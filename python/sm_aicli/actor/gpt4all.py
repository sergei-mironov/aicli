from contextlib import contextmanager
from gpt4all import GPT4All
from copy import deepcopy

from ..types import Conversation, Actor, ActorName, ActorOptions, Utterance, Comment

class GPT4AllActor(Actor):
  temp_default = 0.9

  def __init__(self, name:ActorName, opt:ActorOptions):
    assert mname.provider == "gpt4all"
    super().__init__(name, opt)
    self.gpt4all = GPT4All(model=name.val)
    self.gpt4all.chat_session().__enter__()
    self.break_request = False
    self.cnvdepth = 0

  def __del__(self):
    self.gpt4all.chat_session().__exit__()

  def _sync(self, cnv:Conversation) -> list:
    hist = []
    user_message = ''
    for u in cnv.utterances[self.cnvdepth:]:
      if isinstance(u.actor, User):
        user_message += u.contents
      elif isinstance(u.actor, ModelName):
        if len(user_message)>0:
          hist.append({"role":"user", "content":user_message})
          user_message = ''
        hist.append({"role":"assistant", "content": u.contents})
      else:
        raise ValueError(f"Unknown conversation actor {u.actor}")
    if len(user_message)>0:
      assert len(model_message) == 0
      hist.append({"role":"user", "content":user_message})
    return hist


  def comment_with_text(self, cnv:Conversation) -> Comment:
    self.break_request = False
    new_history = self._sync(cnv)
    assert new_history[-1]["role"] == "user"
    user_message = new_history[-1]["content"]
    self.gpt4all._history.extend(new_history[:-1])

    def _model_callback(*args, **kwargs):
      return not self.break_request
    response = self.gpt4all.generate(
      user_message,
      *args,
      max_tokens=200,
      temp=self.mopt.temperature,
      top_k=40,
      top_p=0.9,
      min_p=0.0,
      repeat_penalty=1.1,
      repeat_last_n=64,
      n_batch=9,
      streaming=True,
      callback=_model_callback,
      **kwargs
    )

    for chunk in response:
      yield chunk
    assert self.gpt4all._history[-1]["role"] == "assistant"
    del self.gpt4all._history[-1]

  def interrupt(self)->None:
    self.break_request = True

  def set_options(self, mopt:ActorOptions)->None:
    old_mopt = self.mopt
    if mopt.num_threads != old_mopt.num_threads:
      if mopt.num_threads is not None:
        self.gpt4all.model.set_thread_count(mopt.num_threads)
    self.mopt = deepcopy(mopt)
    self.mopt.num_threads = self.gpt4all.model.thread_count()
    self.mopt.temperature = mopt.temperature or self.temp_default

