
update_pathvar() {
    case "$(eval echo \"\$$1\")" in
        *$2:*) ;;
        *)
            echo "Adding into $1 value $2"
            eval "export $1=$2:\$$1";;
    esac
}

export PROJECT_SOURCE=`pwd`
export GPT4ALLCLI_ROOT=$PROJECT_SOURCE
update_pathvar "PYTHONPATH" "$PROJECT_SOURCE/python"
update_pathvar "PATH" "$PROJECT_SOURCE/sh"
update_pathvar "PATH" "$PROJECT_SOURCE/python"

alias ipython=ipython.sh

