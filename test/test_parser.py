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
  _assert(r'/set model nthreads 3', r'''
    start
      command
        /set

        model

        nthreads

        number       3
  ''')
  _assert('/set model temp 3.4', r'''
    start
      command
        /set

        model

        temp

        float       3.4
  ''')
  _assert('/set model temp default', r'''
    start
      command
        /set

        model

        temp

        def
  ''')


def test_apikey():
  _assert('/set model apikey "keydata"', r'''
    start
      command
        /set

        model

        apikey

        apikey_string
          apikey
            string_value       keydata
  ''')
  _assert('/set model apikey "file:keyfile"', r'''
    start
      command
        /set

        model

        apikey

        apikey_string
          apikey
            apikey_schema       file
            string_value       keyfile
  ''')
  _assert('/set model apikey "verbatim:keydata"', r'''
    start
      command
        /set

        model

        apikey

        apikey_string
          apikey
            apikey_schema       verbatim
            string_value       keydata
  ''')

def test_model():
  _assert('/model "aaa"', r'''
   start
     command
       /model

       model_string
         model
           string_value       aaa
  ''')
