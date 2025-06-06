#!/bin/sh

set -e -x

litrepl restart ai

testvim.sh >_vim.log 2>&1 <<EOF
:messages clear
:AIPush dummy Hi dummy!
:redir @a
:messages
:redir END
"ap
:w! result
:qa!
EOF

cat result | tail -n 1 > result-filtered

# FIMXE: Get the contents of the vim messages
diff -u result-filtered - <<"EOF"
You said:^@```^@Hi dummy!^@^@Please do not generate any polite endings in your response.^@```^@I say:^@I am a dummy actor 'dummy:default'^@My api key is 'None'^@My temperature is 'None'^@My prompt is 'None'
EOF
