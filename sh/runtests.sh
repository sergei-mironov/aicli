#!/bin/sh

set -e -x
echo "Running pytest"
pytest ./test
for t in ./test/*\.exp ; do
  echo "Running $t"
  $t
done
echo OK
