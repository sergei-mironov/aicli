#!/bin/sh

FILES=
CMD=eval-code
test -n "$LITREPL" || LITREPL=litrepl
test -n "$AICLI_PROMPT" && AICLI_PROMPT="$AICLI_PROMPT "
while [ $# -gt 0 ]; do
  case "$1" in
    -P|--prompt) export AICLI_PROMPT="$AICLI_PROMPT$2"; shift ;;
    -s|--selection-paste) AICLI_PASTEMODE=y; AICLI_SELECTION="$2"; shift ;;
    -S|--selection-raw) AICLI_PASTEMODE=n; AICLI_SELECTION="$2"; shift ;;
    -c|--output-comments-format) AICLI_OCFORMAT="$2"; shift ;;
    -f|--output-format) AICLI_OFORMAT="$2"; shift ;;
    -w|--textwidth) AICLI_TEXTWIDTH="$2"; shift ;;
    -d|--debug) AICLI_DEBUG=y ;;
    --header) AICLI_HEADER="${AICLI_HEADER}$2" ; shift ;;
    --footer) AICLI_FOOTER="${AICLI_FOOTER}$2" ; shift ;;
    -h|--help)
      echo "Usage: $0 [-f|--output-format STR] [-w|--textwidth NUM] \
[-P|--prompt STR] [-c--output-comments-format (none|commented|free)] \
[-(s|S)|--selection[-raw] (FILE|-)] [FILE...] [start|stop|restart|repl] [-- ...]"
      exit 0
      ;;
    start|stop|restart|repl|status|eval-code) CMD=$1 ;;
    --) shift; break ;;
    -*) echo "Invalid argument '$1'">&2; exit 1 ;;
    *) FILES="$FILES $1" ;;
  esac
  shift
done

if test "$CMD" != "eval-code" ; then
  exec $LITREPL "$@" "$CMD" ai
fi

doc() {
  test -n "$AICLI_OFORMAT" && echo -n "$AICLI_OFORMAT" || echo -n "text"
}

debug() {
  if test -n "$AICLI_DEBUG" ; then
    tee /dev/stderr
  else
    cat
  fi
}

{
echo "$AICLI_HEADER"

if test -n "$AICLI_SELECTION" ; then
if test "$AICLI_PASTEMODE" = "y" ; then cat <<EOF
Consider the following text snippet to which we refer as to 'selection':
/paste on
EOF
cat "$AICLI_SELECTION"
cat <<EOF
/paste off

(End of the 'selection' snippet)
EOF
else # PASTEMODE is disabled
cat "$AICLI_SELECTION"
fi
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

echo "$AICLI_PROMPT"

if test -n "$AICLI_OFORMAT" ; then cat <<EOF
Please generate a pastable `doc` without any additional text document
formatting. Please don't use Markdown formatting \`\`\` in your response.

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
fenced|commented) cat <<EOF
For your own comments or questions, if needed, please wrap
them into comment blocks as we normally do in `doc` documents.
Please don't use Markdown formatting \`\`\` in your response.

EOF
;;
*)
;;
esac

if test -n "$AICLI_TEXTWIDTH" ; then cat <<EOF
Please avoid generating lines longer than $AICLI_TEXTWIDTH characters.
EOF
fi

cat <<EOF
Please do not generate any polite endings in your response.
EOF

echo "$AICLI_FOOTER"
} | debug | exec $LITREPL "$@" eval-code ai

