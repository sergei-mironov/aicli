from typing import Any
from openai import OpenAI, OpenAIError, DefaultHttpxClient
from openai.types.image import Image as OpenAIImage
from json import loads as json_loads, dumps as json_dumps
from io import StringIO, BytesIO
from dataclasses import dataclass
from os import makedirs, path
from os.path import join, basename, exists
from requests import get as requests_get
from requests.exceptions import RequestException
from requests import get, exceptions
from hashlib import sha256
from urllib.parse import urlparse, parse_qs
from pdb import set_trace as ST
from collections import OrderedDict

from ..types import (Actor, ActorName, ActorView, PathStr, ActorOptions,
                     Conversation, Intention, ModelName, UserName, Utterance,
                     Modality, ConversationException, SAU, Stream, Contents,
                     File)
from ..utils import (ConsoleLogger, find_last_message, err, uts_2sau,
                     uts_lastfull, uts_lastref, cont2str,
                     add_transparent_rectangle, read_until_pattern)

from .user import CMD_ANS

def url2ext(url)->str|None:
  parsed_url = urlparse(url)
  query_params = parse_qs(parsed_url.query)
  mime_type = query_params.get('rsct', [None])[0].split('/')
  if len(mime_type)==2 and mime_type[0]=='image':
    return f".{mime_type[1]}"
  else:
    return None

def url2fname(url, image_dir:str|None)->str|None:
  ext = url2ext(url)
  base_name = sha256(url.encode()).hexdigest()[:10]
  fname = f"{base_name}{ext}" if ext is not None else base_name
  fdir = image_dir or "."
  return join(fdir,fname)

class TextStream(Stream):
  def __init__(self, chunks):
    def _map(c):
      res = c.choices[0].delta.content
      return res or ''
    super().__init__(map(_map, chunks))
  def gen(self):
    yield from super().gen()

class BinStream(Stream):
  def __init__(self, chunks, **kwargs):
    super().__init__(chunks.iter_content(4*1024), binary=True, **kwargs)
  def gen(self):
    yield from super().gen()

class OpenAIActor(Actor):
  def __init__(self, name:ActorName, opt:ActorOptions, file:File):
    assert isinstance(name, ModelName), name
    assert name.provider == "openai", name.provider
    super().__init__(name, opt)
    self.logger = ConsoleLogger(self)
    self.file = file
    try:
      self.client = OpenAI(api_key=opt.apikey, http_client=DefaultHttpxClient(proxy=opt.proxy))
    except OpenAIError as err:
      raise ValueError(str(err)) from err
    self.reset()

  def reset(self):
    self.logger.dbg("Resetting session")
    self.cache = OrderedDict()

  def _cnv2sau(self, cnv:Conversation) -> SAU:
    """ Convert conversation to the SAU format. """
    sau = uts_2sau(
      cnv.utterances,
      names={UserName():'user'},
      default_name='assistant',
      system_prompt=self.opt.prompt,
      cache=self.cache
    )
    if len(self.cache)>5:
      self.cache.popitem(last=False)
    return sau

  def _react_text(self, act:ActorView, cnv:Conversation) -> Utterance:
    sau = self._cnv2sau(cnv)
    self.logger.dbg(f"sau: {sau}")
    response = []
    if self.opt.replay:
      response = read_until_pattern(self.file, CMD_ANS, 'OpenAI>>> ')
    else:
      try:
        chunks = self.client.chat.completions.create(
          model=self.name.model,
          messages=sau,
          stream=True,
          temperature=self.opt.temperature,
          seed=self.opt.seed,
        )
        response = [TextStream(chunks)]
      except OpenAIError as err:
        raise ConversationException(str(err)) from err
    assert len(response)>0, "Empty response"
    return Utterance.init(self.name, Intention.init(actor_next=UserName()), response)

  def _cnv2cont(self, cnv:Conversation) -> Contents:
    # [1] - id of the request; [2] - non-empty utterance by the same issuer.
    uid = uts_lastref(cnv.utterances, self.name) # [1]
    if uid is not None and cnv.utterances[uid].is_empty():
      refname = cnv.utterances[uid].actor_name
      uid = uts_lastfull(cnv.utterances[:uid], refname) # [2]
    if uid is None:
      raise ConversationException("No meaningful utterance were found")
    return cnv.utterances[uid].contents

  def _read_image_response(self, response) -> list[BinStream]:
    acc = []
    for datum in response.data:
      if not isinstance(datum, OpenAIImage):
        raise ConversationException(f"Wrong datum type ({type(datum)})")
      url = datum.url
      if url is None:
        raise ConversationException(f"Datum url is None")
      self.logger.dbg(url)
      url_response = requests_get(url, stream=True)
      url_response.raise_for_status()  # Check for HTTP errors
      acc.append(BinStream(url_response, suggested_fname=url2fname(url, self.opt.image_dir)))
    return acc

  def _react_image_create(self, act:ActorView, cont:Contents) -> Utterance:
    prompt = cont2str(cont)
    if self.opt.verbose > 0:
      self.logger.dbg(f"create image prompt: {prompt}")
    if self.opt.seed is not None:
      self.logger.warn(f"Image generation does not support seed")
    try:
      response = self.client.images.generate(
        prompt=prompt,
        model=self.name.model,
        n=self.opt.imgnum or 1,
        size=self.opt.imgsz or "256x256",
        response_format="url",
      )
      streams = self._read_image_response(response)
      return Utterance.init(
        name=self.name,
        intention=Intention.init(actor_next=UserName()),
        contents=streams
      )
    except OpenAIError as err:
      raise ConversationException(str(err)) from err
    except RequestException as err:
      raise ConversationException(str(err)) from err

  def _react_image_modify(self, act:ActorView, cont:Contents) -> Utterance:
    bbuf,sbuf = BytesIO(),StringIO()
    for cf in cont:
      if isinstance(cf,bytes):
        bbuf.write(cf)
      elif isinstance(cf,str):
        sbuf.write(cf)
      else:
        assert False, f"Unsupported content fragemnt type {type(cf)}"

    self.logger.dbg(f"Image editing prompt: {sbuf.getvalue()}")
    if self.opt.seed is not None:
      self.logger.warn(f"Image editing does not support seed")
    try:
      response = self.client.images.edit(
        image=bbuf,
        prompt=sbuf.getvalue(),
        model=self.name.model,
        n=self.opt.imgnum or 1,
        size=self.opt.imgsz or "256x256",
        response_format="url"
      )
      streams = self._read_image_response(response)
      return Utterance.init(
        name=self.name,
        intention=Intention.init(actor_next=UserName()),
        contents=streams
      )
    except OpenAIError as err:
      raise ConversationException(str(err)) from err
    except RequestException as err:
      raise ConversationException(str(err)) from err

  def react(self, act:ActorView, cnv:Conversation) -> Utterance:
    if len(cnv.utterances) == 0:
      raise ConversationException(f'No context')
    modality = self.opt.modality
    if modality is None:
      if 'dall' in self.name.model:
        modality = Modality.Image
      else:
        modality = Modality.Text
    if modality == Modality.Text:
      return self._react_text(act, cnv)
    elif modality == Modality.Image:
      cont = self._cnv2cont(cnv)
      if any([isinstance(cf, bytes) for cf in cont]):
        return self._react_image_modify(act, cont)
      else:
        return self._react_image_create(act, cont)
    else:
      raise ConversationException(f'Unsupported modality {modality}')



