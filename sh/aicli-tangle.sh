#!/bin/sh

if test -z "$LITREPL" ; then
  LITREPL=litrepl
fi

{
echo '/set model replay on'
$LITREPL --python-interpreter=- --sh-interpreter=- \
  tangle --before-code=$'/paste on\n' --after-code=$'\n/paste off\n/ask\n' \
         --before-result='' --after-result=$'/ans\n'
echo '/set model replay off'
}
