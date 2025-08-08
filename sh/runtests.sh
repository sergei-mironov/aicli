#!/bin/sh

export AICLI_RC=none
export AICLI_CWD=$AICLI_ROOT
unset AICLI_HISTORY

set -e -x
echo "Running pytest"
pytest -vv ./test
echo "Running shell tests"
for t in $AICLI_ROOT/test/*\.{sh,exp} ; do
  TD="$AICLI_ROOT/_tests/$(basename $t | sed 's/[.-]/_/g')"
  echo "Running $(basename $t) in $TD"
  (
    rm $TD/* || true
    mkdir -p "$TD"
    cd "$TD"
    $t
  )
done
echo OK
