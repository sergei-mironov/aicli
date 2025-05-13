#!/bin/sh

while [ $# -gt 0 ]; do
  case "$1" in
    -P|--prompt) PROMPT="$2"; shift ;;
    --style) PROMPT="Your task is to rephrase the below text so it appears more idiomatic:" ;;
    --grammar) PROMPT="Please correct the grammar in the below text:" ;;
    --code) CODE=y; PROMPT="Please modify the below code. $2"; shift ;;
    -f|--format) FORMAT="$2"; shift ;;
    -w|--textwidth) TEXTWIDTH="$2"; shift ;;
    --no-comments) NOCOMMENTS=y ;;
    -h|--help)
      echo "Usage: $0 [-f|--format <format>] [-w|--textwidth <width>] [-P|--prompt <prompt>]
[--style] [--grammar] [--code <context>] [--no-comments]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" ;;
  esac
  shift
done

doc() {
  test "$CODE" = "y" && echo -n "code" || echo -n "text"
}

{
cat <<EOF
$PROMPT
(start of `doc`)
/paste on
EOF
cat
cat <<EOF
/paste off
(end of `doc`)
Please generate a pastable `doc` without any additional text document formatting.
EOF

if test "$NOCOMMENTS" = "y" ; then
cat <<EOF
Please omit any comments you might want to add, just output the required pastable `doc`.
EOF
elif test -n "$FORMAT" ; then
cat <<EOF
Put your own comments, if any, wrapped into comment blocks as we normally do in $FORMAT documents.
EOF
fi

if test -n "$TEXTWIDTH" ; then
cat <<EOF
Please avoid generating lines longer than $TEXTWIDTH characters.
EOF
fi

echo "/ask"
} | litrepl eval-code ai

