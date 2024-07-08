#!/bin/sh

set -e -x

apt-get update >/dev/null
apt-get install -y -qq net-tools openssh-server
rm -rf /var/lib/apt/lists/*

cat >>/etc/ssh/sshd_config <<EOF
PermitEmptyPasswords yes
EOF

cat >>/etc/profile <<EOF
sudo service ssh start
EOF
