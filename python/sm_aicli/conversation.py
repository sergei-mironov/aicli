from .types import Conversation, Actor


# def cnv_last_message(cnv:Conversation) -> tuple[Actor,str]:
#   assert len(cnv.utterances)>0
#   last_actor = None
#   acc = ""
#   for u in reversed(cnv.utterances):
#     if last_actor is None:
#       last_actor = u.actor
#     if u.actor == last_actor:
#       acc = u.message


  return cnv.utterances[-1]
