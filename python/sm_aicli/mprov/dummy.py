from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps

from .base import ModelProvider, Options

class DummyModelProvider(ModelProvider):
  def __init__(self, model: str, apikey: str, *args, **kwargs):
    self.apikey = apikey
    self.model = model
    print(f"Dummy model '{model}' apikey '{apikey}'")

  def interrupt(self)->None:
    pass

  def get_thread_count(self)->int|None:
    return 1

  def set_thread_count(self, n:int|None)->None:
    pass

  def get_temperature(self)->float|None:
    return 0.0

  def set_temperature(self, t:float|None)->None:
    pass

  @contextmanager
  def with_chat_session(self):
    yield


