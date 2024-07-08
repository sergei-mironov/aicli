from os import environ
from setuptools import setup, find_packages

gpt4all = 'gpt4all-bindings' if 'NIX_PATH' in environ else 'gpt4all >= 2.7.0'

setup(
  name="gpt4all-cli",
  zip_safe=False, # https://mypy.readthedocs.io/en/latest/installed_packages.html
  version="0.0.1",
  package_dir={'':'.'},
  packages=find_packages(where='.'),
  install_requires=[gpt4all, 'gnureadline', 'lark'],
  scripts=['./python//gpt4all-cli'],
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
