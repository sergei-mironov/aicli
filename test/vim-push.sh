#!/bin/sh

set -e -x

litrepl restart ai

testvim.sh >_vim.log 2>&1 <<"EOF"
:messages clear
:redir @a|LPush dummy Hi dummy\!|redir END
"aP
:w! result
:qa!
EOF

diff -u result - <<"EOF"

You said:
```
Hi dummy\!

(Please do not generate any polite endings in your response.)
```
I say:
```
I am a dummy actor 'dummy:default'
My api key is 'None'
My temperature is 'None'
My prompt is 'None'
```
Done
EOF
