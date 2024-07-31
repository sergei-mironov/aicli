from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps

from .base import ModelProvider, Options

class OpenAIModelProvider(ModelProvider):
  def __init__(self, model: str, api_key: str, *args, **kwargs):
    try:
      self.client = OpenAI(api_key=api_key)
      self.model = model
      self.temperature = kwargs.get('temperature', 1.0)
      self.thread_count = kwargs.get('thread_count', None)
      self.interrupt_request = False
    except OpenAIError as err:
      raise ValueError(str(err)) from err

  def stream(self, message: str, *args, opt:Options|None=None, **kwargs):
    try:
      self.interrupt_request = False
      response = self.client.chat.completions.create(
        model=self.model,
        messages=[{"role": "user", "content": message}],
        stream=True,
        temperature=self.temperature,
        **kwargs
      )
      if opt and opt.verbose>0:
        print(response)
      for chunk in response:
        if self.interrupt_request:
          break
        if c := chunk.choices[0].delta.content:
          yield c
    except OpenAIError as err:
      raise ValueError(str(err)) from err

  def interrupt(self) -> None:
    self.interrupt_request = True

  def get_thread_count(self) -> int | None:
    return self.thread_count

  def set_thread_count(self, n: int | None) -> None:
    self.thread_count = n

  def get_temperature(self) -> float | None:
    return self.temperature

  def set_temperature(self, t: float | None) -> None:
    self.temperature = t

  @contextmanager
  def with_chat_session(self):
    yield

