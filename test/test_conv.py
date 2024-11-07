import re
from textwrap import dedent

from sm_aicli import *

def actor(name):
  return ModelName('test',name)

def ut(owner, contents, address):
  return Utterance.init(owner, Intention.init(address), contents)


def test_uts_2sau():
  A = actor('A')
  B = actor('B')
  C = actor('C')
  uts = [ut(A, 'a->b', B), ut(B,'b->a', A), ut(C, 'c->b', B)]
  sau = uts_2sau(uts, {A:'a',B:'b'}, '?', 's', None)
  def _map(sau):
    return [[(k,v) for k,v in d.items()] for d in sau]
  assert _map(sau) == \
    [[('role','system'), ('content','s')],
    [('role','a'), ('content','a->b')],
    [('role','b'), ('content','b->a')],
    [('role','?'), ('content','c->b')]]
  sau = uts_2sau([], {A:'a',B:'b'}, '?', 's', None)
  assert _map(sau) == \
    [[('role','system'), ('content','s')]]

def test_uts_lastref():
  A = actor('A')
  B = actor('B')
  C = actor('C')
  uts = [ut(A, 'a->b', B), ut(B,'b->a', A), ut(C, 'c->b', B)]
  ref = uts_lastref(uts, A)
  assert ref == 1
  ref = uts_lastref([], A)
  assert ref is None


def test_uts_lastfull():
  A = actor('A')
  B = actor('B')
  C = actor('C')
  uts = [ut(B, 'b->a', A), ut(A, 'a->b', B), ut(B, None, A), ut(C, 'c->b', B)]
  ref = uts_lastfull(uts, B)
  assert ref == 0
  ref = uts_lastfull([], B)
  assert ref is None


