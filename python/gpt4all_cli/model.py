from contextlib import contextmanager
from gpt4all import GPT4All


class Model:
  def __init__(self, model:str, *args, **kargs):
    raise NotImplementedError()

  def stream(message:str, *args, **kwargs):
    raise NotImplementedError()

  def interrupt(self)->None:
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
    raise NotImplementedError()



class GPT4AllModel(Model):
  temp_default = 0.9

  def __init__(self, *args, **kwargs):
    self.gpt4all = GPT4All(*args, **kwargs)
    self.temp = GPT4AllModel.temp_default
    self.break_request = False

  def stream(self, message, *args, **kwargs):
    self.break_request = False

    def _model_callback(*args, **kwargs):
      return not self.break_request

    return self.gpt4all.generate(
      message,
      *args,
      # preferential kwargs for chat ux
      max_tokens=200,
      temp=self.temp,
      top_k=40,
      top_p=0.9,
      min_p=0.0,
      repeat_penalty=1.1,
      repeat_last_n=64,
      n_batch=9,
      # required kwargs for cli ux (incremental response)
      streaming=True,
      callback=_model_callback,
      **kwargs
    )

  def interrupt(self)->None:
    self.break_request = True

  def get_thread_count(self)->int|None:
    return self.gpt4all.model.thread_count()

  def set_thread_count(self, n:int|None)->None:
    assert n is not None
    self.gpt4all.model.set_thread_count(n)

  def get_temperature(self)->float|None:
    return self.temp

  def set_temperature(self, t:float|None)->None:
    self.temp = t if t is not None else GPT4AllModel.temp_default

  @contextmanager
  def with_chat_session(self):
    with self.gpt4all.chat_session():
      yield

