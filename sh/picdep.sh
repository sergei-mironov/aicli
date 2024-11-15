#!/bin/sh

set -e

DEPS="doc/*"
SRC="README.md python/*"

echo -n > _used.txt
echo -n > _unused.txt

for D in $DEPS ; do
  S=$(git grep $D || true)
  if test -n "$S" ; then
    echo $D $S >> _used.txt
  else
    echo $D >> _unused.txt
  fi
done

echo USED:
cat _used.txt
echo UNUSED:
cat _unused.txt

echo -n 'Remove unused ? (Ctrl+C to cancel)'
read
rm $(cat _unused.txt)

