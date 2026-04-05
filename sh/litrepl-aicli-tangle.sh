#!/bin/sh

if test -z "$LITREPL" ; then
  LITREPL=litrepl
fi

while test "$#" -gt 0 ; do
    case "$1" in
        -h|--help) echo "TODO"; exit 1 ;;
        -P|--prompt) shift ;;
        -s|--selection-paste) shift ;;
        -S|--selection-raw) shift ;;
        -f|--output-format) shift ;;
        -w|--textwidth) shift ;;
        -v|-d|--debug|--verbose) ;;
        --dry-run) dry_run=1; ;;
        --command) shift ;;
        --) break ;;
        -*) echo "Unknown option: $1" >&2; exit 1 ;;
        *) FILES="$FILES $1" ;;
    esac
    shift
done


tee >(
{
echo '/set model replay on'
$LITREPL --python-interpreter=- --sh-interpreter=- \
  tangle --before-code=$'/paste on\n' --after-code=$'\n/paste off\n/ask\n' \
         --before-result='' --after-result=$'/ans\n'
echo '/set model replay off'
} | $LITREPL eval-code ai "$@" >&2;
)


