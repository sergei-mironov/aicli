import openai
from contextlib import contextmanager
from openai import OpenAI, OpenAIError, NotFoundError

from .base import ModelProvider

class OpenAIModelProvider(ModelProvider):
  def __init__(self, model: str, api_key: str, *args, **kwargs):
    try:
      self.client = OpenAI(api_key=api_key)
      self.model = model
      self.temperature = kwargs.get('temperature', 1.0)
      self.thread_count = kwargs.get('thread_count', None)
    except OpenAIError as err:
      raise ValueError(str(err)) from err

  def stream(self, message: str, *args, **kwargs):
    try:
      response = self.client.chat.completions.create(
        model=self.model,
        messages=[{"role": "user", "content": message}],
        stream=True,
        temperature=self.temperature,
        **kwargs
      )
      for chunk in response:
        if chunk['choices'][0].get('delta'):
          yield chunk['choices'][0]['delta'].get('content', '')
    except NotFoundError as err:
      raise ValueError(str(err)) from err

  def interrupt(self) -> None:
    raise NotImplementedError("Interrupting a streaming request is not directly supported by the OpenAI API.")

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

