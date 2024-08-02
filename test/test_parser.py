import re
from textwrap import dedent

from sm_aicli import *

def _assert(a, tb):
  ta = re.sub(r"^[ \t]+$", '', PARSER.parse(a).pretty().strip().replace('\t', ' '*7), flags=re.MULTILINE)
  tb = re.sub(r"^[ \t]+$", '', dedent(tb).strip().replace('\t', ' '*7), flags=re.MULTILINE)
  assert ta == tb, f"\nExpected:\n{tb}\nGot:\n{ta}"

def test_parser():
  _assert(r'\a', r'''
    start
      escape       \a
  ''')
  _assert('/echo ', '''
    start
      command       /echo
      text
  ''')
  _assert('/echo', '''
    start
      command       /echo
  ''')
  _assert('a/echo', '''
    start
      text       a
      command       /echo
  ''')
  _assert('/echoa', '''
    start
      command       /echo
      text       a
  ''')
  _assert(r'\/echo', r'''
    start
      escape       \/
      text       echo
  ''')
  _assert(r'/echo/echo', r'''
    start
      command       /echo
      command       /echo
  ''')
  _assert('/echo/echoxx', r'''
    start
      command       /echo
      command       /echo
      text       xx
  ''')
  _assert(r'/echo\a', r'''
    start
      command       /echo
      escape       \a
  ''')
  _assert(r'', r'''
    start
  ''')
  _assert(r'/nthreads 3', r'''
    start
      command
        /nthreads

        number       3
  ''')
  _assert('/temp 3.4', r'''
    start
      command
        /temp

        float       3.4
  ''')
  _assert('/temp default', r'''
    start
      command
        /temp

        def
  ''')


def test_apikey():
  _assert('/apikey "keydata"', r'''
    start
      command
        /apikey

        "
        apikey_string
          apikey_value       keydata
        "
  ''')
  _assert('/apikey "file:keyfile"', r'''
    start
      command
        /apikey

        "
        apikey_string
          as_file
          apikey_value       keyfile
        "
  ''')
  _assert('/apikey "verbatim:keydata"', r'''
    start
      command
        /apikey

        "
        apikey_string
          as_verbatim
          apikey_value       keydata
        "
  ''')

def test_model():
  _assert('/model "aaa"', r'''
   start
     command
       /model

       "
       model_string
         model_name       aaa
       "
  ''')
