#!/bin/sh

set -e -x

litrepl restart ai

cat >source <<EOF
Paste-mode file replace
EOF

testvim.sh source >_vim.log 2>&1 <<"EOF"
:LPipeFile dummy Do something\!
:w! result
:qa!
EOF

diff -u result - <<"EOF"
You said:
```
Consider the contents of the file named "source":

Paste-mode file replace

(End of "source" contents)

Do something!

(Please do not generate any polite endings in your response.)
```
I say:
```
I am a dummy actor 'dummy:default'
My api key is 'None'
My temperature is 'None'
My prompt is 'None'
```
EOF
