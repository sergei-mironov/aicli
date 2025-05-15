#!/bin/sh

export AICLI_PROMPT="$AICLI_PROMPT Please check and fix the grammar of the \"selection\"."
exec aicli-eval.sh "$@"
