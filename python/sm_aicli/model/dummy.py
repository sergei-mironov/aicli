from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from itertools import cycle

from ..types import Model, ModelName, ModelOptions

class DummyModel(Model):

  def __init__(self, mname:ModelName, mopt:ModelOptions):
    super().__init__(mname, mopt)
    self.interrupt = False
    print(f"Dummy model '{self.mname}' apikey '{self.mopt.apikey}'")

  def interrupt(self)->None:
    self.interrupt = True

  def ask_for_message_stream(self, cnv:Conversation):
    """ Return a token generator object, responding the message. """
    self.interrupt = False
    for chunk in cycle(["dummy"]):
      if not self.interrupt:
        yield chunk

  def ask_for_image(self, cnv:Conversation) -> PathStr:
    """ Return a path to generated image, responding the message. """
    raise NotImplementedError()
