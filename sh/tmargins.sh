#!/bin/sh
# From https://superuser.com/a/1491469/1092923

pane="${2:-$TMUX_PANE}"
[ -n "$pane" ] || exit 1
tmux has-session -t "$pane" 2>/dev/null || exit 0

tool="$0"
width="${TMUX_M_COLUMNS:-80}"
step=10
todo="${TMUX_M_COMMAND:-true}"
action="$1"
pattern=" '$tool' sleep "
pattern_left="$pattern'${pane}' left"
pattern_right="$pattern'${pane}' right"
command_left="TMUX_M_COMMAND='$todo'$pattern_left"
command_right="TMUX_M_COMMAND='$todo'$pattern_right"

tmux display-message -p '#{pane_start_command}' | grep -qF "$pattern" && exit 0

find_margins() {
    pane_left="$(tmux list-panes -F "#{pane_id} #{pane_start_command}" | grep -F "$pattern_left" | head -n 1 | cut -d ' ' -f 1)"
    pane_right="$(tmux list-panes -F "#{pane_id} #{pane_start_command}" | grep -F "$pattern_right" | head -n 1 | cut -d ' ' -f 1)"
}

find_geometry() {
    [ -n "$pane_left" ] && width_left="$(tmux display-message -p -t "$pane_left" '#{pane_width}')" || width_left=0
    [ -n "$pane_right" ] && width_right="$(tmux display-message -p -t "$pane_right" '#{pane_width}')" || width_right=0

    border=0
    [ "$width_left" -gt 0 ] && border=$((border+1))
    [ "$width_right" -gt 0 ] && border=$((border+1))

        width_center="$(tmux display-message -t "$pane" -p '#{pane_width}')"
    width_all="$((width_center+width_left+width_right+border))"

    [ "$((width+5))" -ge "$width_all" ] && width="$width_all"
}

destroy() {
    [ -n "$pane_left" ] && [ "$pane_left" != "$TMUX_PANE" ] && tmux kill-pane -t "$pane_left"
    [ -n "$pane_right" ] && [ "$pane_right" != "$TMUX_PANE" ] && tmux kill-pane -t "$pane_right"
    [ "$pane_left" = "$TMUX_PANE" ] || [ "$pane_right" = "$TMUX_PANE" ] && tmux kill-pane -t "$TMUX_PANE"
    true
}


create() {
    width_left=$(( (width_all-width-2)/2 ))
    [ "$width_left" -gt 2 ] || width_left=2
    if [ -n "$pane_left" ]; then
        tmux resize-pane -t "$pane_left" -x "$width_left"
    else
        tmux split-window -hdbl "$width_left" -t "$pane" "$command_left"
    fi

        width_right=$(( width_all-width-width_left-2 ))
        [ "$width_right" -gt 2 ] || width_right=2
    if [ -n "$pane_right" ]; then
        tmux resize-pane -t "$pane_right" -x "$width_right"
    else
        tmux split-window -hdl "$width_right" -t "$pane" "$command_right"
    fi
}

equalize() {
        width="$width_center"
    [ "$width" -lt "$width_all" ] && create
}

verify() {
    tmux has-session -t "$pane" 2>/dev/null || destroy
}

resize() {
    width="$((width_center${1}))"
    if [ "$((width+5))" -ge "$width_all" ]; then
        destroy
    else
        create
    fi
}

main() {
    find_margins
    find_geometry
    case "$action" in
        sleep )
            trap destroy INT
            trap 'verify; kill "$!" 2>/dev/null; $todo &' WINCH
            while true; do
                $todo &
                while sleep 1; do verify; done
            done
        ;;
        ""|c* )
            create
        ;;
        d* )
            destroy
        ;;
        e* )
            equalize
        ;;
        + )
            resize "+$step"
        ;;
        - )
            resize "-step"
        ;;
        +*|-* )
            resize "$action"
        ;;
    esac
}

main
