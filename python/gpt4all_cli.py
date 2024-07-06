#!/usr/bin/env python

import io
from gnureadline import parse_and_bind, set_completer
from gpt4all import GPT4All
from argparse import ArgumentParser
from contextlib import contextmanager
from signal import signal, SIGINT, SIGALRM, setitimer, ITIMER_REAL


def completer(text, state):
  options = [cmd for cmd in commands if cmd.startswith(text)]
  if state < len(options):
    return options[state]
  else:
    return None


def read_multiline_input(initial_prompt=">>> ", intermediate_prompt="... "):
  lines = []
  prompt = initial_prompt
  while True:
    try:
      line = input(prompt)
      if " " not in line.strip():
        lines.append(line)
        break
      elif line == "":
        break
      else:
        lines.append(line)
        pass
      prompt = intermediate_prompt
    except EOFError:
      break
  return lines


# Define some example commands
commands = ["help", "list", "exit", "start", "stop", "restart"]

# Set up GNU readline
parse_and_bind("tab: complete")
set_completer(completer)


def adjust_thread_count(gpt4all_instance, num_threads=None):
  if num_threads is not None:
    curr_num_threads = gpt4all_instance.model.thread_count()
    print(f"Adjusted: {curr_num_threads} →", end="")
    gpt4all_instance.model.set_thread_count(num_threads)
    new_num_threads = gpt4all_instance.model.thread_count()
    print(f" {new_num_threads} threads", flush=True)
  else:
    new_num_threads = gpt4all_instance.model.thread_count()
    print(f"Using {new_num_threads} threads", flush=True)
  return new_num_threads


def parse_args():
  parser = ArgumentParser(description="Command-line arguments")
  parser.add_argument(
    "--model", "-m",
    type=str,
    help="Model to use for chatbot",
    # FIXME:
    # default="mistral-7b-instruct-v0.1.Q4_0.gguf",
    default='/home/grwlf/.local/share/nomic.ai/GPT4All/Meta-Llama-3-8B-Instruct.Q4_0.gguf'
  )
  parser.add_argument(
    "--n-threads", "-t",
    type=int,
    help="Number of threads to use for chatbot",
    default=None
  )
  parser.add_argument(
    "--device", "-d",
    type=str,
    help="Device to use for chatbot, e.g. gpu, amd, nvidia, intel. Defaults to CPU.",
    default=None
  )
  return parser.parse_args()


@contextmanager
def with_sigint(_handler):
  """ A Not very correct singal handler. One also needs to mask signals during switching handlers """
  prev=signal(SIGINT,_handler)
  try:
    yield
  finally:
    signal(SIGINT,prev)


def ask1(gpt4all_instance, message:str) -> str|None:
  response = io.StringIO()
  try:
    break_request = False

    def _signal_handler(signum,frame):
      nonlocal break_request
      print(f"Handling SIGINT")
      break_request = True

    def _model_callback(*args, **kwargs):
      return not break_request

    response_generator = gpt4all_instance.generate(
      message,
      # preferential kwargs for chat ux
      max_tokens=200,
      temp=0.9,
      top_k=40,
      top_p=0.9,
      min_p=0.0,
      repeat_penalty=1.1,
      repeat_last_n=64,
      n_batch=9,
      # required kwargs for cli ux (incremental response)
      streaming=True,
      callback=_model_callback
    )

    with with_sigint(_signal_handler):
      for token in response_generator:
        print(token, end='', flush=True)
        response.write(token)

  finally:
    response.close()
  return response

def main():
  args = parse_args()
  gpt4all_instance = GPT4All(args.model, device=args.device)
  adjust_thread_count(gpt4all_instance, args.n_threads)

  with gpt4all_instance.chat_session():
    exit_request = False
    while not exit_request:
      buffer = []
      for line in read_multiline_input():
        if line.strip() == "ask":
          message = '\n'.join(buffer)
          ask1(gpt4all_instance, message)
          buffer.clear()
        elif line.strip() == "exit":
          exit_request = True
          break
        else:
          buffer.append(line)

if __name__ == "__main__":
  main()
