#!/bin/sh

set -x -e

venv=$1
workdir=$2
user_id=$3
user_name=$4
group_id=$5
group_name=$6

test -n "$workdir"
test -n "$user_id" && test -n "$user_name"
test -n "$group_id" && test -n "$group_name"

userdel `id -nu "${user_id}"` || true
addgroup --gid "${group_id}" "${group_name}" || true
adduser --gid "${group_id}" --uid "${user_id}" \
  --disabled-password --quiet "${user_name}"
# usermod --gid "${group_id}" --uid "${user_id}" \
#   --disabled-password --quiet "${user_name}"
usermod -a -G sudo "${user_name}"

echo "${user_name} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-nopasswd-sudo

passwd -d $user_name

cat >>/etc/profile <<EOF
export PATH=\$HOME/.local/bin:\$PATH
EOF

cat >>/etc/profile <<EOF
if which ccache >/dev/null && test -d "$workdir"; then
  ccache --set-config=cache_dir="$workdir/_ccache"
  ccache -M 20G
  /usr/sbin/update-ccache-symlinks
fi
EOF

cat >>/etc/profile <<EOF
if test -d "$workdir" ; then
    rm \$HOME/.bash_history 2>/dev/null || true
    touch $workdir/_bash_history
    ln -s $workdir/_bash_history \$HOME/.bash_history
fi
EOF

mkdir -pv $venv
chown "$user_name:$group_name" $venv
sudo -iu $user_name python3 -m venv $venv
cat >>/etc/profile <<EOF
if test -f $venv/bin/activate ; then
    . $venv/bin/activate
fi
EOF

cat >>/etc/bash.bashrc <<EOF
if test -n "\$PS1" ; then
  cd $workdir
fi
if test -f "$workdir/env.sh" ; then
  . $workdir/env.sh
fi
EOF

if test -f /etc/bash.bashrc ; then
    sed -i 's/^\( *\).*\(PS1=.*\)/\1true # !not setting \2/g' /etc/bash.bashrc
fi
if test -f /home/$user_name/.bashrc ; then
    sed -i 's/^\( *\).*\(PS1=.*\)/\1true # !not setting \2/g' /home/$user_name/.bashrc
fi

