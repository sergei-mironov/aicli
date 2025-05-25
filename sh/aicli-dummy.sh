#!/bin/sh

CMD=eval-code
test -n "$LITREPL" || LITREPL=litrepl
while [ $# -gt 0 ]; do
  case "$1" in
    -P|--prompt) export AICLI_PROMPT="$AICLI_PROMPT$2"; shift ;;
    start|stop|restart|repl|status|eval-code) CMD=$1 ;;
    --) shift; break ;;
    *) echo "Invalid argument '$1'">&2; exit 1 ;;
  esac
  shift
done

if test "$CMD" != "eval-code" ; then
  exec $LITREPL "$@" "$CMD" ai
else
  { echo "/model dummy" ; cat ; } | exec $LITREPL "$@" "$CMD" ai
fi
