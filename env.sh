
update_pathvar() {
    case "$(eval echo \"\$$1\")" in
        *$2:*) ;;
        *)
            echo "Adding into $1 value $2"
            eval "export $1=$2:\$$1";;
    esac
}

export PROJECT_SOURCE=`pwd`
export PROJECT_ROOT=`pwd`
export VIM_PLUGINS="$PROJECT_SOURCE/vim"
export AICLI_ROOT=$PROJECT_SOURCE
export AICLI_HISTORY=$PROJECT_SOURCE/_aicli_history
update_pathvar "PYTHONPATH" "$PROJECT_SOURCE/python"
update_pathvar "PATH" "$PROJECT_SOURCE/sh"
update_pathvar "PATH" "$PROJECT_SOURCE/python"

alias ipython=ipython.sh

export LITREPL_WORKDIR="$PROJECT_SOURCE"
export LITREPL_PYTHON_AUXDIR="$PROJECT_SOURCE/_litrepl/python"
export LITREPL_AI_AUXDIR="$PROJECT_SOURCE/_litrepl/ai"
