from sm_aicli import *

import pytest
from copy import deepcopy

def test_stream_deepcopy():
  def _gen():
    yield "FOO"
    yield "BAR"
  s = Stream(_gen())
  with pytest.raises(AssertionError):
    deepcopy(deepcopy(s))
  lines=[s for s in s.gen()]
  assert lines==["FOO","BAR"]
  s2 = deepcopy(deepcopy(s))
