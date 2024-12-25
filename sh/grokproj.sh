#!/bin/sh
# Loads a project into an AI model using Litrepl as a session manager.

set -e

if test -z "$LITREPL_AI_AUXDIR" ; then
  export LITREPL_AI_AUXDIR=`pwd`/_litrepl/ai
fi

PNAME=$(basename "$(pwd)")

usage() {
  echo "Usage: $0 [--verbose] [--restart] [-h|--help] [(-N |--project-name=)NAME] EXT"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --verbose)
      set -x
      shift
      ;;
    --restart)
      litrepl restart ai
      shift
      ;;
    -N)
      PNAME=$2
      shift
      shift
      ;;
    --project-name=*)
      PNAME=$(echo "$1" | sed 's/^--project-name=//')
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      EXT="$1"
      shift
      break
      ;;
  esac
done

if test -z "$EXT"; then
  usage
  exit 1
fi

{
cat <<EOF
Consider the following software project. Next I will send it to you file-by-file.

$PNAME
========

EOF

for f in `find -name "*.$EXT"` ; do
  echo ""
  echo "File: $f"
  echo '```'
  echo '/paste on'
  cat $f
  echo '/paste off'
  echo '```'
done
} | litrepl eval-code ai

