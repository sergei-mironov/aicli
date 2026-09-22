#!/usr/bin/env bash

if test -z "$LITREPL" ; then
  LITREPL=litrepl
fi

TW=''
LOC=''
DRYRUN=false
while test "$#" -gt 0 ; do
    case "$1" in
        -h|--help) echo "TODO"; exit 1 ;;
        -P|--prompt) shift ;;
        -s|--selection-paste) shift ;;
        -S|--selection-raw) shift ;;
        -f|--output-format) shift ;;
        -w|--textwidth) TW="--textwidth $2" ; shift; shift ;;
        -v|-d|--debug|--verbose) ;;
        --dry-run) DRYRUN=true; ;;
        --command) shift ;;
        --loc) LOC=$2; shift; shift;;
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
         --before-result='' --after-result=$'/ans\n' $LOC
echo '/set model replay off'
} | $LITREPL eval-code ai $TW >&2;
)


