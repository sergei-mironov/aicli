
class ModelProvider:
  def __init__(self, model:str, *args, **kargs):
    raise NotImplementedError()

  def stream(message:str, *args, **kwargs):
    """ Return a token generator object, responding the message. """
    raise NotImplementedError()

  def interrupt(self)->None:
    """ Interrupt the token generation started by `stream`. Might be called from a signal. """
    raise NotImplementedError()

  def get_thread_count()->int|None:
    raise NotImplementedError()

  def set_thread_count(n:int|None)->None:
    raise NotImplementedError()

  def get_temperature(self)->float|None:
    raise NotImplementedError()

  def set_temperature(self, t:float|None)->None:
    raise NotImplementedError()

  def with_chat_session():
    """ A context manager doing arbitrary initialization """
    raise NotImplementedError()

