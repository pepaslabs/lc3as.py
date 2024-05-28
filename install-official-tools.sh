#!/bin/bash

# Install the official LC-3 assembler as published by McGraw-Hill.
# See https://highered.mheducation.com/sites/0072467509/student_view0/lc-3_simulator.html

set -e -o pipefail

if test -e ~/opt/lc3tools-0.12/lc3as ; then
    echo "Already installed."
    exit 0
fi

set -x

cd /tmp
if ! test -e lc3tools_v12.zip ; then
    curl --fail --location --remote-name http://highered.mheducation.com/sites/dl/free/0072467509/104652/lc3tools_v12.zip
fi
rm -rf lc3tools
unzip lc3tools_v12.zip
cd lc3tools
./configure --installdir ~/opt/lc3tools-0.12
make install

mkdir -p ~/opt/lc3tools-0.12/doc
cd ~/opt/lc3tools-0.12/doc
curl --fail --location --remote-name https://highered.mheducation.com/sites/dl/free/0072467509/104652/LC3_unix.pdf
curl --fail --location --remote-name https://highered.mheducation.com/sites/dl/free/0072467509/104691/pat67509_appa.pdf

mkdir -p ~/bin
cd ~/bin
ln -sf ~/opt/lc3tools-0.12/lc3{as,convert,sim,sim-tk} .
