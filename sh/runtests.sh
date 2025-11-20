#!/bin/sh

export AICLI_RC=none
export AICLI_CWD=$AICLI_ROOT
unset AICLI_HISTORY

set -e -x
echo "Running pytest"
pytest -vv ./test
echo "Running shell tests"
for t in $AICLI_ROOT/test/*\.{sh,exp} ; do
  TN=$(basename $t)
  if echo $TN | grep -q vim- ; then
    if test -n "$VIM_LITREPL" ; then
      echo "Skipping $TN"
      continue
    fi
  fi
  TD="$AICLI_ROOT/_tests/$(echo $TN | sed 's/[.-]/_/g')"
  echo "Running $TN in $TD"
  (
    rm $TD/* || true
    mkdir -p "$TD"
    cd "$TD"
    $t
  )
done
echo OK
