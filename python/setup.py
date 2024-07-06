from setuptools import setup, find_packages

with open("README.md", "r") as f:
  long_description = f.read()

setup(
  name="gpt4all-cli",
  zip_safe=False, # https://mypy.readthedocs.io/en/latest/installed_packages.html
  version="0.0.1",
  package_dir={'':'.'},
  packages=find_packages(where='.'),
  long_description=long_description,
  long_description_content_type="text/markdown",
  install_requires=['gpt4all-bindings', 'gnureadline'],
  scripts=['./gpt4all_cli.py'],
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
