#!/bin/sh

set -e -x

litrepl restart ai

cat >source <<EOF
Pull test
=========
EOF


testvim.sh source >_vim.log 2>&1 <<EOF
/=========
:AI dummy Hi dummy\\!
:w! result
:qa!
EOF

diff -u result - <<"EOF"
Pull test
=========
You said:
```
Hi dummy!

Please do not generate any polite endings in your response.
```
I say:
I am a dummy actor 'dummy:default'
My api key is 'None'
My temperature is 'None'
My prompt is 'None'
EOF
