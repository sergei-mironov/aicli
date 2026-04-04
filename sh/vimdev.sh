#!/bin/sh

# This is a small shell wrapper which adds LitREPL plugin from the current
# repository to the VIM's runtime path.
VIM=`which vim`
PATH=\
$AICLI_ROOT/python:$AICLI_ROOT/sh:\
$(dirname `which git`):\
$(dirname `which python`):\
$(dirname `which litrepl`):\
$(dirname $(readlink $(readlink `which ondir`)))\
  exec $VIM "$@"

