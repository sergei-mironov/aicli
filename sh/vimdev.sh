#!/bin/sh

# This is a small shell wrapper which adds LitREPL plugin from the current
# repository to the VIM's runtime path.

if ! test -f "$PROJECT_ROOT/vim/plugin/aicli.vim" ; then
  echo "'aicli.vim' is not under the PROJECT_ROOT. Did you source 'env.sh'?" >&2
  exit 1
fi
exec vim -c "
if exists('g:aicli_loaded')
  unlet g:aicli_loaded
endif

if exists(':AI')
  delcommand AI
endif

if exists(':AIP')
  delcommand AIP
endif

if exists(':AIF')
  delcommand AIF
endif

let &runtimepath = '$PROJECT_ROOT/vim,'.&runtimepath
runtime plugin/aicli.vim
" "$@"

