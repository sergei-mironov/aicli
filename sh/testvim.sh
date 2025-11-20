#!/bin/sh

set -e

if test -n "$VIM_LITREPL" ; then
  echo "Please set VIM_LITREPL to a valid litrepl Vim plugin"
  exit 1
fi

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
  echo ":source $VIM_LITREPL/plugin/litrepl.vim"
  echo ":source $VIM_LITREPL/plugin/litrepl_extras.vim"
  cat
} | \
$AICLI_ROOT/sh/vimdev.sh -n --clean "$@" >_vim.log
not grep -E '^E[0-9]+|Error' _vim_messages.log
not grep -E '^E[0-9]+:' _vim.log
