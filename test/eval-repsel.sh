#!/bin/sh

set -e -x

litrepl restart ai

cat >source <<EOF
Replace selection test
======================
xxx
EOF

testvim.sh source >_vim.log 2>&1 <<EOF
/xxx
V\
:AI dummy -
:w! result
:qa!
EOF

diff -u result - <<"EOF"
Replace selection test
======================
You said:
```
Consider the following text snippet to which we refer as to 'selection':

xxx

(End of the 'selection' snippet)

Please do not generate any polite endings in your response.
```
I say:
I am a dummy actor 'dummy:default'
My api key is 'None'
My temperature is 'None'
My prompt is 'None'
EOF
