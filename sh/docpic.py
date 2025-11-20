#!/usr/bin/env python

import sys
from os import makedirs, system
from hashlib import sha256
from textwrap import dedent

def docpic(tex, width='10%'):
  texdoc = dedent(
    r"""
    \documentclass{standalone}
    \usepackage{tikz-cd}
    \begin{document}
    """) + tex + r"\end{document}"
  makedirs('doc', exist_ok=True)
  fn = sha256(texdoc.encode()).hexdigest()[:10]
  with open(f"doc/{fn}.tex", 'w') as f:
    f.write(texdoc)
  ret = system(f'cd doc && pdflatex --interaction=nonstopmode {fn}.tex >_docpic.err 2>&1')
  assert ret == 0, (ret, fn)
  # ret = system(f'cd doc && convert -density 300 {fn}.pdf -quality 90 {fn}.png')
  ret = system(f'cd doc && pdf2svg {fn}.pdf {fn}.svg')
  assert ret == 0, (ret, fn)
  print(f'<img src="doc/{fn}.svg" width="{width}" />')

def main():
  tex = sys.stdin.read().strip()
  width = sys.argv[1] if len(sys.argv) == 2 else '10%'
  docpic(tex, width)

if __name__ == "__main__":
  main()
