#!/bin/sh

if test -z "$LITREPL" ; then
  LITREPL=litrepl
fi

{
echo '/set model replay on'
$LITREPL --python-interpreter=- --sh-interpreter=- \
  tangle --after-code=$'/ask\n' --after-result=$'/ans\n'
echo '/set model replay off'
}
