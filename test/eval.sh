#!/bin/sh

set -e -x

cat >source <<EOF
Dummy
---
---
EOF

testvim.sh source >_vim.log 2>&1 <<EOF
1G
:AI dummy -
:w! result
:qa!
EOF

diff -u result - <<EOF
Dummy
---
I am a dummy actor 'dummy:default'
My api key is 'None'
My temperature is 'None'
My prompt is 'None'
---
EOF
