#!/bin/sh

export AICLI_RC=none

set -e -x
echo "Running pytest"
pytest -vv ./test
for t in ./test/*\.exp ; do
  echo "Running $t"
  $t
done
echo OK
