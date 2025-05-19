#!/bin/sh

FILES=
test -n "$AICLI_PROMPT" && AICLI_PROMPT="$AICLI_PROMPT "
while [ $# -gt 0 ]; do
  case "$1" in
    -P|--prompt) export AICLI_PROMPT="$AICLI_PROMPT$2"; shift ;;
    -s|--selection) AICLI_SELECTION="$2"; shift ;;
    -c|--output-comments-format) AICLI_OCFORMAT="$2"; shift ;;
    -f|--output-format) AICLI_OFORMAT="$2"; shift ;;
    -w|--textwidth) AICLI_TEXTWIDTH="$2"; shift ;;
    -d|--debug) AICLI_DEBUG=y ;;
    -h|--help)
      echo "Usage: $0 [-f|--output-format STR] [-w|--textwidth NUM] \
[-P|--prompt STR] [-c--output-comments-format (none|commented|free)] \
[-s|--selection (FILE|-)] [FILE...] [-- ...]"
      exit 0
      ;;
    --) shift; break ;;
    -*) echo "Invalid argument '$1'">&2; exit 1 ;;
    *) FILES="$FILES $1" ;;
  esac
  shift
done

doc() {
  test -n "$AICLI_OFORMAT" && echo -n "$AICLI_OFORMAT" || echo -n "text"
}

cat_() {
  case "$1" in
    -) cat ;;
    *) cat "$1" ;;
  esac
}

debug() {
  if test -n "$AICLI_DEBUG" ; then
    tee /dev/stderr
  else
    cat
  fi
}

{
if test -n "$AICLI_SELECTION" ; then cat <<EOF
Consider the following text snippet named 'selection':

/paste on
EOF
cat_ $AICLI_SELECTION
cat <<EOF
/paste off
(End of the 'selection' snippet)
EOF
fi

for f in $FILES; do if test -f "$f" ; then cat <<EOF
Consider the contents of the file named '$f':

/append file:"$f" buffer:"in"
(End of '$f' contents)
EOF
else
echo "No such file: $f" >&2
fi
done

cat <<EOF
Your task is the following:

$AICLI_PROMPT

EOF

if test -n "$AICLI_SELECTION" -a -z "$FILES" ; then cat <<EOF
Please generate a pastable `doc` without any additional text document
formatting. Your response should perfectly fit in place of the below
'selection' snippet.  Please don't use Markdown formatting \`\`\` in your
response.

EOF
elif test -z "$AICLI_SELECTION" -a -n "$FILES" ; then cat <<EOF
Please generate a pastable `doc` without any additional text document
formatting. Your response should perfectly fit into $FILES.
Please don't use Markdown formatting \`\`\` in your response.

EOF
fi

if test -n "$AICLI_OFORMAT" ; then cat <<EOF
Please generate the response which follows the $AICLI_OFORMAT format.

EOF
fi

case $AICLI_OCFORMAT in
no|none|empty) cat <<EOF
Please generate no comments. Do not ask questions.

EOF
;;
any|free) cat <<EOF
Feel free to put your own comments or questions in a free form.

EOF
;;
*|fenced|commented) cat <<EOF
For your own comments or questions, if needed, please wrap
them into comment blocks as we normally do in `doc` documents.

EOF
;;
esac

if test -n "$AICLI_TEXTWIDTH" ; then cat <<EOF
Please avoid generating lines longer than $AICLI_TEXTWIDTH characters.
EOF
fi

cat <<EOF
Please do not generate any polite endings in your response.
EOF
} | debug | litrepl "$@" eval-code ai

