from typing import Any
from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from io import StringIO
from dataclasses import dataclass

from ..types import (Actor, ActorName, ActorView, PathStr, ActorOptions, Conversation,
                     ActorResponse, ModelName, UserName, Utterance)
from ..utils import expand_apikey

@dataclass
class OpenAIUtterance(Utterance):
  chunks:Any
  stop:bool=False
  def interrupt(self):
    self.stop = True
  def gen(self):
    self.stop = False
    self.contents = ''
    try:
      for chunk in self.chunks:
        if self.stop:
          break
        if text:=chunk.choices[0].delta.content:
          self.contents += text
          yield text
    except OpenAIError as err:
      yield f"<ERROR: {str(err)}>"

class OpenAIActor(Actor):
  def __init__(self, name: ActorName, opt: ActorOptions):
    assert isinstance(name, ModelName), name
    assert name.provider == "openai", name.provider
    super().__init__(name, opt)
    self.cnvtop = 0
    self.messages = [{"role": "system", "content": "You are a helpful assistant."}]
    try:
      self.client = OpenAI(api_key=expand_apikey(opt.apikey))
    except OpenAIError as err:
      raise ValueError(str(err)) from err

  def comment_with_text(self, act:ActorView, cnv:Conversation) -> ActorResponse:
    for i in range(self.cnvtop, len(cnv.utterances)):
      u = cnv.utterances[i]
      assert isinstance(u.contents, str)
      role = "user" if u.actor_name == UserName() else "assistant"
      self.messages.append({"role":role, "content": u.contents})
      self.cnvtop += 1

    try:
      chunks = self.client.chat.completions.create(
        model=self.name.model,
        messages=self.messages,
        stream=True,
        temperature=self.opt.temperature,
      )
      return ActorResponse.init(
        actor_next=UserName(),
        utterance=OpenAIUtterance(self.name, None, chunks)
      )
    except OpenAIError as err:
      raise ValueError(str(err)) from err

  # def ask_image(self, prompt:str, *args, opts:ActorOptions|None=None, **kwargs) -> PathStr:
  #   response = self.client.images.generate(
  #     prompt=prompt,
  #     model=self.model_name.val,
  #     n=1,
  #     size="512x512",
  #     response_format="url")
  #   print(response)

