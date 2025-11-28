#!/usr/bin/env python
import os
import sys
import argparse
import subprocess

from textwrap import dedent
from contextlib import contextmanager
from io import StringIO
from typing import Optional, List, Any

DEFAULT_FORMAT = "text"

def doc(args) -> str:
  """Return output format name (a)."""
  return args.output_format or DEFAULT_FORMAT # (a)

def projectlocal(file_path:str, project_root:str) -> str:
  """Return file_path relative to project_root if set (a)."""
  if project_root: # (a)
    return os.path.relpath(file_path, project_root)
  return file_path

def leading_spaces(s:str) -> str:
  """Return leading spaces of a string (a)."""
  i = 0
  while i < len(s) and s[i] == " ":
    i += 1
  return s[:i]

def compute_indent_prefix(selection_text:str) -> str:
  """Compute common leading-space prefix of nonempty lines.  Skip empty/whitespace-only lines (a).
  Initialize from the first nonempty line (b). Truncate by min length for each next line (c)."""
  prefix = None
  for line in selection_text.split('\n'):
    if not line.strip():  # (a)
      continue
    ls = leading_spaces(line)  # (c)
    if prefix is None:
      prefix = ls  # (b)
      continue
    prefix = prefix[:min(len(prefix), len(ls))]  # (c)
  return prefix or ""


@contextmanager
def open_or_stdin(name, mode):
  if name == "-":
    assert mode == 'r'
    yield sys.stdin
  else:
    with open(name, mode) as f:
      yield f


def asline(text:str, prefix:str|None=None) -> str:
  return (' ' if prefix is None else prefix) + dedent(text).replace('\n', ' ').strip()

def build_prompt(args, project_root:str, do_dedent:bool=True):
  """Build the complete prompt sent to litrepl (a), and compute indent prefix for later output
  reindentation (b). The function first collects any header/footer text (c), then incorporates
  either a pasted or file-based selection (d), followed by per-file context blocks (e), an
  optional user prompt (f), and finally a set of meta-instructions controlling the model output
  (g); at the end, it also prepares indentation information based on the captured selection lines
  (h)."""
  header = args.header[0] if args.header else ""
  footer = args.footer[0] if args.footer else ""

  lines = StringIO() # (a)
  reindent_prefix = ""

  if header:
    lines.write(header) # (c)
    lines.write("\n")

  on,off = "on","off"
  selection = args.selection_paste or args.selection_raw

  if selection: # (d)
    lines.write(dedent(f'''\
      Consider the following text snippet to which we refer as to 'selection':
    '''))
    if args.selection_paste:
      lines.write(dedent(f'''\
        /paste {on}
      '''))

    lines.write('\n')
    with open_or_stdin(selection, "r") as f:
      selection_text = str(sys.stdin.read())
      if do_dedent:
        reindent_prefix = compute_indent_prefix(selection_text) # (h)
        selection_text = dedent(selection_text)
      lines.write(selection_text)
    lines.write('\n')

    if args.selection_paste:
      if f"/paste {off}" in selection_text:
        sys.stderr.write(f"WARNING: '/paste {off}' command found in the selection")
      lines.write(dedent(f'''\
        /paste {off}
      '''))
    lines.write(dedent(f'''\
      (End of the 'selection' snippet)
    '''))


  for file in args.files: # (e)
    if os.path.isfile(file):
      rel = projectlocal(file, project_root)
      lines.write(dedent(f'''\
        Consider the contents of the file named "{rel}":

        /append file:"{file}" buffer:"in"

        (End of "{rel}" contents)
      '''))
    else:
      sys.stderr.write(f"No such file: {file}\n")

  if args.prompt: # (f)
    lines.write("\n")
    lines.write(args.prompt)
    lines.write("\n\n")

  lines.write("(")

  lines.write(
    asline("Please do not generate any polite endings in your response.", prefix='')
  ) # (g)

  ofmt = args.output_format

  if ofmt is not None:
    if ofmt != DEFAULT_FORMAT:
      lines.write(asline(f'''
        Please generate a pastable fragment of {doc(args)} document. Specifically, please do not
        wrap your response with the Markdown- or Latex-style code blocks of any kind.
      '''))
    if ofmt in ["python", "sh", "cpp", "c"]:
      lines.write(asline(f'''
        Feel free to put your own comments into {doc(args)} comment blocks.
      '''))

  if args.textwidth:
    lines.write(asline(f"Please avoid generating lines longer than {args.textwidth} characters."))

  lines.write(")")

  if footer:
    lines.write("\n")
    lines.write(footer)
    lines.write("\n")

  lines.write("/ask\n")
  return lines.getvalue(), reindent_prefix # (b)


litrepl_path = os.getenv("LITREPL", "litrepl")
project_root = os.getenv("PROJECT_ROOT", "")

def main():
  """Parse CLI options (a), handle non-eval commands via exec (b), build an AI prompt with
  optional selection-based indent (c), run litrepl eval-code (d), and reindent its output using
  the computed indent prefix (e)."""
  parser = argparse.ArgumentParser(add_help=True)  # (a)
  parser.add_argument("-P", "--prompt", dest="prompt", default="", type=str)
  parser.add_argument("-s", "--selection-paste", dest="selection_paste", default=None, type=str)
  parser.add_argument("-S", "--selection-raw", dest="selection_raw", default=None, type=str)
  parser.add_argument("-f", "--output-format", dest="output_format", type=str)
  parser.add_argument("-w", "--textwidth", dest="textwidth", type=int)
  parser.add_argument("-v", "-d", "--debug", "--verbose", dest="debug", action="store_true")
  parser.add_argument("--dry-run", action="store_true")
  parser.add_argument("--no-reindent", action="store_true")
  parser.add_argument("--header", dest="header", nargs=1, default=None)
  parser.add_argument("--footer", dest="footer", nargs=1, default=None)
  parser.add_argument("command", nargs="?", default="eval-code")
  parser.add_argument("files", nargs=argparse.REMAINDER)

  args = parser.parse_args()  # (a)
  cmd = args.command

  if cmd != "eval-code":  # (b)
    run_args = [litrepl_path] + args.files + [cmd, "ai"]
    os.execvp(litrepl_path, run_args)

  prompt_text, reindent_prefix = build_prompt(
    args, project_root, do_dedent=not args.no_reindent)  # (c)

  if args.debug:
    sys.stderr.write(f"REINDENT PREFIX (len {len(reindent_prefix)}):\n")
    sys.stderr.write(reindent_prefix)
    sys.stderr.write("\nPROMPT:\n")
    sys.stderr.write(prompt_text)

  if args.dry_run:
    exit(0)

  proc = subprocess.Popen(
    [litrepl_path, "eval-code", "ai"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=sys.stderr,
    text=True,
  )
  try:
    stdout_data, _ = proc.communicate(prompt_text)
  except BrokenPipeError:
    stdout_data = ""

  for line in StringIO(stdout_data):
    sys.stdout.write(f"{reindent_prefix}{line}") # (e)

  sys.exit(proc.returncode if proc.returncode is not None else 0)  # (d)

if __name__ == "__main__":
  main()
