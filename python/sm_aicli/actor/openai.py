from typing import Any
from openai import OpenAI, OpenAIError, DefaultHttpxClient
from openai.types.image import Image as OpenAIImage
from json import loads as json_loads, dumps as json_dumps
from io import StringIO, BytesIO
from dataclasses import dataclass
from os import makedirs, path
from os.path import join, basename, exists
# from requests import get, exceptions
from pdb import set_trace as ST
from collections import OrderedDict
from os import stat

from ..types import (Actor, ActorName, ActorState, PathStr, ActorOptions, Conversation, Intention,
                     ModelName, UserName, Utterance, ConversationException, SAU, Stream, Contents,
                     File, LocalReference, RemoteReference, ContentItem)

from ..utils import (ConsoleLogger, IterableStream, find_last_message, err, uts_2sau, uts_lastfull,
                     uts_lastref, add_transparent_rectangle, read_until_pattern, TextStream)

from .user import CMD_ANS

OpenAIFileID = str


class OpenAIImageActor(Actor):
  def __init__(self, name:ActorName, opt:ActorOptions, file:File):
    assert isinstance(name, ModelName), name
    assert name.provider == "openai", f"Unsupported provider '{name.provider}'"
    assert 'dall' in name.model, f"Unsupported model '{name.model}'"
    super().__init__(name, opt)
    self.logger = ConsoleLogger(self)
    try:
      self.client = OpenAI(api_key=opt.apikey, http_client=DefaultHttpxClient(proxy=opt.proxy))
    except OpenAIError as err:
      raise ValueError(str(err)) from err
    self.reset()

  def reset(self):
    self.logger.dbg("Resetting session")
    self.cache = OrderedDict()

  def _cnv2cont(self, cnv:Conversation) -> Contents:
    # [1] - id of the request; [2] - non-empty utterance by the same issuer.
    uid = uts_lastref(cnv.utterances, self.name) # [1]
    if uid is not None and cnv.utterances[uid].is_empty():
      refname = cnv.utterances[uid].actor_name
      uid = uts_lastfull(cnv.utterances[:uid], refname) # [2]
    if uid is None:
      raise ConversationException("No meaningful utterance were found")
    return cnv.utterances[uid].contents

  def _read_image_response(self, response) -> list[ContentItem]:
    acc = []
    for datum in response.data:
      if not isinstance(datum, OpenAIImage):
        raise ConversationException(f"Wrong datum type ({type(datum)})")
      url = datum.url
      if url is None:
        raise ConversationException(f"Datum url is None")
      self.logger.dbg(url)
      acc.append(RemoteReference('image',url))
    return acc

  def _react_image_create(self, act:ActorState, prompt:str) -> Utterance:
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
      content = self._read_image_response(response)
      return Utterance.init(
        name=self.name,
        intention=Intention.init(actor_next=UserName()),
        contents=IterableStream(content)
      )
    except OpenAIError as err:
      raise ConversationException(str(err)) from err
    except RequestException as err:
      raise ConversationException(str(err)) from err

  def _react_image_modify(self, act:ActorState, prompt:str, image:BytesIO) -> Utterance:
    self.logger.dbg(f"Image editing prompt: {prompt}")
    if self.opt.seed is not None:
      self.logger.warn(f"Image editing does not support seed")
    try:
      response = self.client.images.edit(
        image=image,
        prompt=prompt,
        model=self.name.model,
        n=self.opt.imgnum or 1,
        size=self.opt.imgsz or "256x256",
        response_format="url"
      )
      content = self._read_image_response(response)
      return Utterance.init(
        name=self.name,
        intention=Intention.init(actor_next=UserName()),
        contents=IterableStream(content)
      )
    except OpenAIError as err:
      raise ConversationException(str(err)) from err
    except RequestException as err:
      raise ConversationException(str(err)) from err

  def react(self, act:ActorState, cnv:Conversation) -> Utterance:
    if len(cnv.utterances) == 0:
      raise ConversationException(f'No context')
    cont = self._cnv2cont(cnv)
    bbuf,sbuf = None,StringIO()
    for cf in cont.gen():
      match cf:
        case bytes():
          if bbuf is None:
            bbuf = BytesIO()
          bbuf.write(cf)
        case str():
          sbuf.write(cf)
        case _:
          raise ValueError(f"Unsupported content type: {cf}")
    if bbuf is not None:
      return self._react_image_modify(act, sbuf.getvalue(), bbuf)
    else:
      return self._react_image_create(act, sbuf.getvalue())


class OpenAITextActor(Actor):
  def __init__(self, name:ActorName, opt:ActorOptions, file:File):
    assert isinstance(name, ModelName), name
    assert name.provider == "openai", f"Unsupported provider '{name.provider}'"
    assert 'gpt-4' in name.model, f"Unsupported model '{name.model}'"

    super().__init__(name, opt)
    self.logger = ConsoleLogger(self)
    self.file = file
    self.uploads:dict[LocalReference,OpenAIFileID] = {}
    try:
      self.client = OpenAI(api_key=opt.apikey, http_client=DefaultHttpxClient(proxy=opt.proxy))
    except OpenAIError as err:
      raise ValueError(str(err)) from err
    self.reset()

  def reset(self):
    self.logger.dbg("Resetting session")
    self.cache = OrderedDict()

  def upload_reference_cached(self, ref:LocalReference) -> OpenAIFileID:
    assert isinstance(ref, LocalReference), f"Not a LocalReference: {ref}"
    if file_id := self.uploads.get(ref):
      return file_id
    upload = self.client.uploads.upload_file_chunked(
      file = ref.path,
      mime_type = ref.mimetype,
      purpose = "assistants",
    )
    self.logger.dbg(f"{ref} upload status: {upload.status} file_id {upload.file.id}")
    assert upload.status == "completed"
    self.uploads[ref] = upload.file.id
    return self.uploads[ref]

  def _cnv2sau(self, cnv:Conversation) -> SAU:
    """ Convert conversation to the extended SAU format. """
    def _cont2str(c:Contents) -> list:
      acc = []
      def _append_text(text):
        if len(acc) == 0 or acc[-1]['type'] != 'text':
          acc.append({'type':'text', 'text':''})
        if acc[-1]['type'] == 'text':
          acc[-1]['text'] += text
      for tok in c.gen():
        match tok:
          case str():
            _append_text(tok)
          case bytes():
            _append_text(tok.decode('utf-8'))
          case LocalReference():
            file_id = self.upload_reference_cached(tok)
            acc.append({'type':'file', 'file':{'file_id':file_id}})
          case _:
            raise ValueError(f"Unsupported content item: {tok}")
      return acc

    sau = uts_2sau(
      cnv.utterances,
      names={UserName():'user'},
      default_name='assistant',
      system_prompt=self.opt.prompt,
      cache=self.cache,
      cont2str_fn=_cont2str,
    )
    if len(self.cache)>5:
      self.cache.popitem(last=False)
    return sau

  def _react_text(self, act:ActorState, cnv:Conversation) -> Utterance:
    sau = self._cnv2sau(cnv)
    self.logger.dbg(f"sau: {sau}")
    response = None
    if self.opt.replay:
      response = IterableStream(read_until_pattern(self.file, CMD_ANS, 'OpenAI>>> '))
    else:
      try:
        chunks = self.client.chat.completions.create(
          model=self.name.model,
          messages=sau,
          stream=True,
          temperature=self.opt.temperature,
          seed=self.opt.seed,
        )
        response = TextStream(chunks)
      except OpenAIError as err:
        raise ConversationException(str(err)) from err
    assert response is not None
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

  def react(self, act:ActorState, cnv:Conversation) -> Utterance:
    if len(cnv.utterances) == 0:
      raise ConversationException(f'No context')
    sau = self._cnv2sau(cnv)
    self.logger.dbg(f"sau: {sau}")
    response = None
    if self.opt.replay:
      response = IterableStream(read_until_pattern(self.file, CMD_ANS, 'OpenAI>>> '))
    else:
      try:
        chunks = self.client.chat.completions.create(
          model=self.name.model,
          messages=sau,
          stream=True,
          temperature=self.opt.temperature,
          seed=self.opt.seed,
        )
        response = TextStream(chunks)
      except OpenAIError as err:
        raise ConversationException(str(err)) from err
    assert response is not None
    return Utterance.init(self.name, Intention.init(actor_next=UserName()), response)

