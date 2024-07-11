import sys
from os import environ
from os.path import join, dirname
from setuptools import setup, find_packages
from logging import getLogger
from subprocess import check_output
logger=getLogger(__name__)
warning=logger.warning

REVISION:str|None
try:
  REVISION=environ["GPT4ALLCLI_REVISION"]
except Exception as e:
  warning("Couldn't read GPT4ALLCLI_REVISION, trying `git rev-parse`")
  try:
    REVISION=check_output(['git', 'rev-parse', 'HEAD'],
                           cwd=dirname(__file__)).decode().strip()
  except Exception as e:
    warning(e)
    warning("Couldn't use `git rev-parse`, no revision metadata will be set")
    REVISION=None

if REVISION:
  with open(join('python','gpt4all_cli', 'revision.py'), 'w') as f:
    f.write("# AUTOGENERATED by setup.exe!\n")
    f.write(f"REVISION = '{REVISION}'\n")

gpt4all = 'gpt4all-bindings' if 'NIX_PATH' in environ else 'gpt4all >= 2.7.0'

setup(
  name="gpt4all-cli",
  zip_safe=False, # https://mypy.readthedocs.io/en/latest/installed_packages.html
  version="0.0.1",
  package_dir={'':'python'},
  packages=find_packages(where='.'),
  install_requires=[gpt4all, 'gnureadline', 'lark'],
  scripts=[join('.','python','gpt4all-cli')],
  python_requires='>=3.6',
  author="Sergei Mironov",
  author_email="sergei.v.mironov@proton.me",
  description="Command-line interface using GPT4ALL bindings",
  classifiers=[
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: POSIX :: Linux",
    "Topic :: Software Development :: Build Tools",
    "Intended Audience :: Developers",
    "Development Status :: 3 - Alpha",
  ],
)
