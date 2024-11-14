import re
from textwrap import dedent
from pytest import raises
from lark.exceptions import LarkError

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

        3
  ''')
  _assert('/set model temp 3.4', r'''
    start
      command
        /set

        model

        temp

        3.4
  ''')
  _assert('/set model temp default', r'''
    start
      command
        /set

        model

        temp

        default
  ''')


def test_apikey():
  _assert('/set model apikey "keydata"', r'''
    start
      command
        /set

        model

        apikey

        ref
          string
            string_value       keydata
  ''')
  _assert('/set model apikey file:"key file"', r'''
    start
      command
        /set

        model

        apikey

        ref
          file
          string
            string_value       key file
  ''')
  _assert('/set model apikey verbatim:keydata', r'''
    start
      command
        /set

        model

        apikey

        ref
          verbatim
          string
            string_value       keydata
  ''')

def test_model_1():
  _assert('/model "aaa"', r'''
    start
      command
        /model

        model_ref
          string
            string_value       aaa
  ''')

def test_model_2():
  _assert('/model openai:"aaa bbb"', r'''
    start
      command
        /model

        model_ref
          openai
          string
            string_value       aaa bbb
  ''')
  _assert('/model openai:gpt-4o xxx', r'''
    start
      command
        /model

        model_ref
          openai
          string
            string_value       gpt-4o
      text        xxx
  ''')

def test_ref_01():
  _assert('/cat aaa', r'''
     start
       command
         /cat

         ref
           string
             string_value       aaa
  ''')

def test_ref_1():
  _assert('/cat "aaa"', r'''
    start
      command
        /cat

        ref
          string
            string_value       aaa
  ''')

def test_ref_2():
  _assert('/cat file:aaa', r'''
    start
      command
        /cat

        ref
          file
          string
            string_value       aaa
  ''')

def test_ref_3():
  _assert('/cat verbatim:aaa', r'''
    start
      command
        /cat

        ref
          verbatim
          string
            string_value       aaa
  ''')

def test_ref_4():
  _assert('/cat buffer:aaa', r'''
    start
      command
        /cat

        ref
          buffer
          string
            string_value       aaa
  ''')

def test_ref_5():
  _assert('/cat verbatim:aaa', r'''
    start
      command
        /cat

        ref
          verbatim
          string
            string_value       aaa
  ''')
  _assert('/cat verbatim:aaa\n', r'''
    start
      command
        /cat

        ref
          verbatim
          string
            string_value       aaa
      text
  ''')

def test_ref_6():
  """ Here the `aaa/cat` is parsed as a file name and the `verbatim:bbb` is parsed as text """
  _assert('/cat file:aaa/cat text', r'''
    start
      command
        /cat

        ref
          file
          string
            string_value       aaa/cat
      text        text
  ''')

def test_ref_7():
  _assert('/cat file:"file with spaces"', r'''
    start
      command
        /cat

        ref
          file
          string
            string_value       file with spaces
  ''')

def test_ref_file():
  _assert('/cat file(buffer:a)', r'''
    start
      command
        /cat

        ref_file
          file
          (
          ref
            buffer
            string
              string_value       a
          )
  ''')

def test_invalid_string():
  """ Does not raise an error on ill-formatted strings """
  _assert('/cat "aaa', r'''
    start
      text       /cat "aaa
  ''')

def test_slash():
  """ Does not raise an error on command-looking texts """
  _assert('just/text', r'''
    start
      text       just
      text       /text
  ''')

def test_comment():
  _assert('# /echo aaa\n/echo bbb', r'''
    start
      text       

      command       /echo
      text        bbb
  ''')
