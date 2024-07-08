#!/bin/sh

# TODO: Merge with `install_user.sh`

set -x -e

user_name=$1
git_name=$2
git_email=$3

test -n "$git_name"
test -n "$git_email"

sudo -iu $user_name git config --global user.name "$git_name"
sudo -iu $user_name git config --global user.email "$git_email"
sudo -iu $user_name git config --global credential.helper "cache --timeout 180000"

# Required by a custom `glc` wrapper
apt-get update >/dev/null
apt-get install -y -qq rlwrap
rm -rf /var/lib/apt/lists/*
