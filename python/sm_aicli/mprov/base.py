from dataclasses import dataclass

PathStr = str
ModelName = str

@dataclass
class Options:
  """ Aicli options """
  verbose:int=0

@dataclass
class ModelSpec:
  text: ModelName
  image: ModelName|None = None

class ModelProvider:
  def __init__(self, models:ModelSpec, *args, **kargs):
    raise NotImplementedError()

  def ask_message_stream(self, message:str, *args, opts:Options|None=None, **kwargs):
    """ Return a token generator object, responding the message. """
    raise NotImplementedError()

  def ask_image(self, prompt:str, *args, opts:Options|None=None, **kwargs) -> PathStr:
    """ Return a path to generated image, responding the message. """
    raise NotImplementedError()

  def interrupt(self)->None:
    """ Interrupt the token generation started by `stream`. Might be called from a signal. """
    raise NotImplementedError()

  def get_thread_count(self)->int|None:
    raise NotImplementedError()

  def set_thread_count(self, n:int|None)->None:
    raise NotImplementedError()

  def get_temperature(self)->float|None:
    raise NotImplementedError()

  def set_temperature(self, t:float|None)->None:
    """ TODO: Move to Options? """
    raise NotImplementedError()

  def with_chat_session(self):
    """ A context manager doing arbitrary initialization """
    raise NotImplementedError()

