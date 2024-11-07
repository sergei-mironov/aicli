from typing import Any
from contextlib import contextmanager
from openai import OpenAI, OpenAIError
from openai.types.image import Image as OpenAIImage
from json import loads as json_loads, dumps as json_dumps
from io import StringIO
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

from ..types import (Actor, ActorName, ActorView, PathStr, ActorOptions, Conversation,
                     Intention, ModelName, UserName, Utterance, Resource, Modality,
                     ConversationException, SAU)
from ..utils import (expand_apikey, dbg, find_last_message, err, uts_2sau, uts_lastfull,
                     uts_lastref)


def url2ext(url)->str|None:
  parsed_url = urlparse(url)
  query_params = parse_qs(parsed_url.query)
  mime_type = query_params.get('rsct', [None])[0].split('/')
  if len(mime_type)==2 and mime_type[0]=='image':
    return f".{mime_type[1]}"
  else:
    return None

def download_url(url, folder_path, ext=None)->str|None:
  if not exists(folder_path):
    makedirs(folder_path)
  try:
    response = requests_get(url, stream=True)
    response.raise_for_status()  # Check for HTTP errors
    base_name = sha256(url.encode()).hexdigest()[:10]
    fname = f"{base_name}{ext}" if ext is not None else base_name
    fpath = join(folder_path, fname)
    with open(fpath, 'wb') as file:
      for chunk in response.iter_content(1024):
        file.write(chunk)
    return fpath
  except RequestException as e:
    err(f"An error occurred: {e}")
  return None


@dataclass
class OpenAIUtterance(Utterance):
  chunks:Any|None=None
  stop:bool=False
  def interrupt(self):
    self.stop = True
  def init(name, intention, contents=None, chunks=None):
    def _gen(self):
      self.stop = False
      self.contents = ''
      try:
        for chunk in chunks:
          if self.stop:
            break
          if text:=chunk.choices[0].delta.content:
            self.contents += text
            yield text
      except OpenAIError as err:
        yield f"<ERROR: {str(err)}>"
    gen =  _gen if chunks is not None else None
    return OpenAIUtterance(name, intention, None, gen)


class OpenAIActor(Actor):
  def __init__(self, name:ActorName, opt:ActorOptions, image_dir:str):
    assert isinstance(name, ModelName), name
    assert name.provider == "openai", name.provider
    super().__init__(name, opt)
    self.image_dir = image_dir
    try:
      self.client = OpenAI(api_key=expand_apikey(opt.apikey))
    except OpenAIError as err:
      raise ValueError(str(err)) from err
    self.reset()

  def reset(self):
    dbg("Resetting session", actor=self)
    self.cnvtop = 0
    self.messages = []
    self.cache = OrderedDict()

  # def _sync(self, cnv:Conversation):
  #   assert self.cnvtop < len(cnv.utterances)
  #   if self.messages == []:
  #     prompt = self.opt.prompt or "You are a helpful assistant."
  #     self.messages = [{"role": "system", "content": prompt}]
  #   for i in range(self.cnvtop, len(cnv.utterances)):
  #     u = cnv.utterances[i]
  #     if u.contents is not None:
  #       role = "user" if u.actor_name == UserName() else "assistant"
  #       self.messages.append({"role":role, "content": u.contents})
  #       self.cnvtop += 1
  #   dbg(f"messages: {self.messages}", actor=self)
  #   assert len(self.messages)>0

  def _cnv2sau(self, cnv:Conversation) -> SAU:
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

  def _cnv2prompt(self, cnv:Conversation) -> str:
    uid = uts_lastref(cnv.utterances, self.name)
    if uid is not None and cnv.utterances[uid].is_empty():
      refname = cnv.utterances[uid].actor_name
      uid = uts_lastfull(cnv.utterances[:uid], refname)
    if uid is None:
      raise ConversationException("no prompt")
    prompt = cnv.utterances[uid].contents
    assert prompt is not None, f"Prompt {uid} has no contents. Is it a thunk?"
    return prompt

  def _react_text(self, act:ActorView, cnv:Conversation) -> Utterance:
    sau = self._cnv2sau(cnv)
    if self.opt.verbose > 0:
      dbg(f"sau: {sau}", actor=self)
    try:
      chunks = self.client.chat.completions.create(
        model=self.name.model,
        messages=sau,
        stream=True,
        temperature=self.opt.temperature,
      )
      return OpenAIUtterance.init(self.name, Intention.init(actor_next=UserName()), chunks=chunks)
    except OpenAIError as err:
      raise ConversationException(str(err)) from err

  def _react_image(self, act:ActorView, cnv:Conversation) -> Utterance:
    prompt = self._cnv2prompt(cnv)
    if self.opt.verbose > 0:
      dbg(f"prompt: {prompt}", actor=self)
    try:
      response = self.client.images.generate(
        prompt=prompt,
        model=self.name.model,
        n=1,
        size=self.opt.imgsz or "256x256",
        response_format="url"
      )
      resources = []
      for datum in response.data:
        if isinstance(datum, OpenAIImage):
          url = datum.url
          if url is not None:
            dbg(url, actor=self)
            ext = url2ext(url)
            path = download_url(url, self.image_dir, ext)
            if path is not None:
              dbg(f"Url successfully saved as '{path}'", actor=self)
              resources.append(Resource.img(path))
            else:
              err(f'Failed to download {url}', actor=self)
        else:
          dbg(f'Skipping non-image response {datum}', actor=self)

      return Utterance.init(
        name=self.name,
        intention=Intention.init(actor_next=UserName()),
        resources=resources
      )
    except OpenAIError as err:
      raise ConversationException(str(err)) from err

  def react(self, act:ActorView, cnv:Conversation) -> Utterance:
    if len(cnv.utterances) == 0:
      raise ConversationException(f'No context')
    modality = cnv.utterances[-1].intention.modality
    if modality == Modality.Text:
      return self._react_text(act, cnv)
    elif modality == Modality.Image:
      return self._react_image(act, cnv)
    else:
      raise ConversationException(f'Unsupported modality {modality}')



