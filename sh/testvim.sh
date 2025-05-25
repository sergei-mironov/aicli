#!/bin/sh

not() {(
  set +e
  $@
  if test "$?" = "0" ; then
    exit 1
  else
    exit 0
  fi
)}

{
  echo ":redir > _vim_messages.log"
  echo ":let g:aicli_errfile='_aicli.err'"
  cat
} | \
$PROJECT_ROOT/sh/vimdev.sh -n --clean "$@"
not grep -E '^E[0-9]+|Error' _vim_messages.log
