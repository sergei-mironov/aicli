#!/bin/sh

export AICLI_NORC=y
exec expect -f "$@"
