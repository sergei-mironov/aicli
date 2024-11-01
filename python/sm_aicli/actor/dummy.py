from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from json import loads as json_loads, dumps as json_dumps
from itertools import cycle

from ..types import Actor, ActorName, ActorOptions, ActorView, Comment, Conversation

class DummyActor(Actor):

  def __init__(self, name:ActorName, act:ActorView, opt:ActorOptions):
    super().__init__(name, opt)
    self.interrupt = False
    print(f"Dummy actor '{self.name}' apikey '{self.opt.apikey}'")

  def interrupt(self)->None:
    self.interrupt = True

  def comment_with_text(self, act:ActorView, cnv:Conversation) -> Comment:
    """ Return a token generator object, responding the message. """
    self.interrupt = False
    for chunk in cycle(["dummy"]):
      if not self.interrupt:
        yield chunk

  def ask_for_image(self, cnv:Conversation) -> Comment:
    """ Return a path to generated image, responding the message. """
    raise NotImplementedError()
