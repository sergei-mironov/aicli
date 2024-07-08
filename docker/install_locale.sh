#!/bin/sh

set -e -x
apt-get update # >/dev/null
apt-get install -y -qq locales tzdata
rm -rf /var/lib/apt/lists/*

echo "America/Toronto" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata
sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
echo 'LANG="en_US.UTF-8"'>/etc/default/locale
dpkg-reconfigure --frontend=noninteractive locales
update-locale LANG=en_US.UTF-8
