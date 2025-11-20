#!/bin/sh

set -e -x

litrepl restart ai

cat >source <<EOF
Paste-mode replace
==================
xxx
  xxx /echo AAA

Raw replace
===========
yyy /echo AAA
EOF

testvim.sh source >_vim.log 2>&1 <<EOF
/xxx
V\
j\
:LPipe dummy -
/yyy
V\
:LPipe! dummy -
:w! result
:qa!
EOF

diff -u result - <<"EOF"
Paste-mode replace
==================
You said:
```
Consider the following text snippet to which we refer as to 'selection':

xxx
  xxx /echo AAA

(End of the 'selection' snippet)

(Please do not generate any polite endings in your response.)
```
I say:
```
I am a dummy actor 'dummy:default'
My api key is 'None'
My temperature is 'None'
My prompt is 'None'
```

Raw replace
===========
AAA
You said:
```
yyy

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
