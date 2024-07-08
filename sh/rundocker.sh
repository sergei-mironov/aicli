#!/bin/sh

# CWD=$(cd `dirname $0`; pwd;)
CWD=`pwd`
DWD=/workspace

GITHACK=n
# MAPPORTS=`expr $UID - 1000`
MAPPORTS=""
DOCKER_FILENAME=$CWD/docker/dev.dockerfile
DOCKER_IMGNAME=""
DOCKER_SUDO="sudo --set-home -D $DWD -u #$(id -u) --preserve-env "
DOCKER_COMMAND="bash --login"
DOCKER_NIX=y
DOCKER_DETACHED_ARGS="-d"
DOCKER_ATTACH_USING_SSH="y"

while test -n "$1" ; do
  case "$1" in
    -h|--help)
      echo "Usage: $0 [-m INT|--map-ports-base INT]"\
                     "[-d|--detached|--ssh]"\
                     "[--no-sudo]"\
                     "[--no-nix]"\
                     "(FILE_NAME.docker|DOCKER_IMAGE_NAME)"\
                     "[-- COMMAND [ARG1 [ARG2..]]]" >&2
      exit 1
      ;;
    -m|--map-ports-base)
      MAPPORTS="$2"; shift
      ;;
    --no-sudo)
      DOCKER_SUDO=""
      ;;
    --no-nix)
      DOCKER_NIX=n
      ;;
    -d|--detached)
      DOCKER_DETACHED_ARGS="-d"
      ;;
    --ssh)
      DOCKER_DETACHED_ARGS="-d"
      DOCKER_ATTACH_USING_SSH="y"
      ;;
    --no-ssh)
      DOCKER_DETACHED_ARGS=""
      DOCKER_ATTACH_USING_SSH="n"
      ;;
    --) shift
      DOCKER_COMMAND=""
      while test -n "$1"; do
        DOCKER_COMMAND="$DOCKER_COMMAND $1"
        shift
      done
      break
      ;;
    *)
      if test -f "$1" ; then
        DOCKER_FILENAME="$1"
      else
        DOCKER_IMGNAME="$1"
      fi
      ;;
  esac
  shift
done

# Remap detach key to Ctrl+e,e
DOCKER_CFG="/tmp/docker-$UID"
mkdir "$DOCKER_CFG" 2>/dev/null || true
cat >$DOCKER_CFG/config.json <<EOF
{ "detachKeys": "ctrl-e,e" }
EOF

set -e -x

if test -n "$DOCKER_IMGNAME" ; then
  docker pull "$DOCKER_IMGNAME:latest"
else
  DOCKER_SUFFIX=`echo $DOCKER_FILENAME | sed -n 's@\([^/]*/\)*\([^_]*_\)\?\([^.]*\)\.dockerfile$@\3@p'`
  if test -z "$DOCKER_SUFFIX" ; then
    DOCKER_SUFFIX="dev"
  fi
  DOCKER_IMGNAME=gpt4all-cli/$DOCKER_SUFFIX

  # DOCKER_BUILDKIT=1 \
  docker build \
    --build-arg=workdir=$DWD \
    --build-arg=user_id=$(id -u) \
    --build-arg=group_id=$(id -g) \
    --build-arg=user_name=$(id -un) \
    --build-arg=git_name="$(git config user.name)" \
    --build-arg=git_email="$(git config user.email)" \
    --build-arg=group_name=$(id -gn) \
    --build-arg=http_proxy=$https_proxy \
    --build-arg=https_proxy=$https_proxy \
    --build-arg=ftp_proxy=$https_proxy \
    -t "$DOCKER_IMGNAME" \
    -f "$DOCKER_FILENAME" \
    "$CWD/docker"

    # "$CWD/docker"
fi

if which buildnix.sh >/dev/null && test "$DOCKER_NIX" = "y" ; then
    sh $(dirname $0)/buildnix.sh --impure
else
    echo "Skipping nix embedding" >&2
fi


if test -n "$MAPPORTS"; then
  PORT_TENSORBOARD=`expr 6000 + $MAPPORTS`
  PORT_JUPYTER=`expr 8888 + $MAPPORTS`

  DOCKER_PORT_ARGS="
    -p 0.0.0.0:$PORT_TENSORBOARD:6006 -e PORT_TENSORBOARD=$PORT_TENSORBOARD
    -p 0.0.0.0:$PORT_JUPYTER:8888 -e PORT_JUPYTER=$PORT_JUPYTER
    -p 22122:22"
fi

# To allow X11 connections from docker
xhost +local: || true
cp "$HOME/.Xauthority" "$CWD/.Xauthority" || true

if which nvidia-docker >/dev/null 2>&1; then
  DOCKER_CMD=nvidia-docker
else
  DOCKER_CMD=docker
fi

# Mount additional folders inside the container
if test -d "/home/data" ; then
  DOCKER_MOUNT_ARGS="$DOCKER_MOUNT_ARGS -v /home/data:/home/data"
fi
if test -d "/nix" ; then
  DOCKER_MOUNT_ARGS="$DOCKER_MOUNT_ARGS -v /nix:/nix"
fi
if test -d "/tmp/.X11-unix" ; then
  DOCKER_MOUNT_ARGS="$DOCKER_MOUNT_ARGS -v /tmp/.X11-unix:/tmp/.X11-unix"
fi
if test -d "/dev/bus/usb" ; then
  DOCKER_MOUNT_ARGS="$DOCKER_MOUNT_ARGS --privileged -v /dev/bus/usb:/dev/bus/usb"
fi

dockermain() {
  ${DOCKER_CMD} --config "$DOCKER_CFG" \
    run -it --rm \
    --hostname="$(hostname)+docker" \
    --volume "$CWD:$DWD" \
    --workdir "$DWD" \
    -m 32g \
    -e "DISPLAY=$DISPLAY" \
    -e "EDITOR=$EDITOR" \
    -e "TERM=$TERM" \
    ${DOCKER_PORT_ARGS} \
    ${DOCKER_MOUNT_ARGS} \
    ${DOCKER_DETACHED_ARGS} \
    --cap-add=SYS_PTRACE \
    --security-opt seccomp=unconfined \
    --privileged -v /dev/bus/usb:/dev/bus/usb \
    "${DOCKER_IMGNAME}" \
    "$@"
}

dockerip() {
  docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$1"
}

tryseticon() {
  if which xseticon 2>/dev/null && test -n "$WINDOWID" ; then
    if test -f "$DOCKER_SUFFIX.png" ; then
      xseticon -id "$WINDOWID" "$DOCKER_SUFFIX.png"
    fi
  fi
}

if test -n "$DOCKER_DETACHED_ARGS" ; then
  if test "$DOCKER_ATTACH_USING_SSH" = "y" ; then
    tryseticon
    CID=$(dockermain bash -c 'service ssh start && bash' | tail -n 1)
    CIP=$(dockerip $CID)
    sleep 1
    exec ssh "-o StrictHostKeyChecking=no" $CIP "$@"
  else
    dockermain $DOCKER_SUDO $DOCKER_COMMAND
  fi
else
  tryseticon
  dockermain $DOCKER_SUDO $DOCKER_COMMAND
fi
