
update_pathvar() {
    case "$(eval echo \"\$$1\")" in
        *$2:*) ;;
        *)
            echo "Adding into $1 value $2"
            eval "export $1=$2:\$$1";;
    esac
}

if test -z "$PROJECT_ROOT" ; then
    export PROJECT_ROOT=`pwd`
fi
export AICLI_ROOT=`pwd`
export AICLI_HISTORY=$AICLI_ROOT/_aicli_history
update_pathvar "PYTHONPATH" "$AICLI_ROOT/python"
update_pathvar "PATH" "$AICLI_ROOT/sh"
update_pathvar "PATH" "$AICLI_ROOT/python"
update_pathvar "PATH" "$AICLI_ROOT/test"

alias ipython=ipython.sh

export LITREPL_WORKDIR="$AICLI_ROOT"
export LITREPL_PYTHON_AUXDIR="$AICLI_ROOT/_litrepl/python"
export LITREPL_AI_AUXDIR="$AICLI_ROOT/_litrepl/ai"

export VIM_PLUGINS="$AICLI_ROOT/vimrc"

# FIXME: Do we need the below?
# unset vim
# unset VIMRUNTIME
