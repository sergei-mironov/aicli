#!/bin/sh

export AICLI_PROMPT="$AICLI_PROMPT rephrase the \"selection\" so it appears more idiomatic."
exec aicli-eval.sh "$@"
