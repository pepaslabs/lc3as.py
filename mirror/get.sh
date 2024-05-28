#!/bin/bash

set -e

# See also https://highered.mheducation.com/sites/0072467509/

CURL='curl --fail --remote-name --location'

if ! test -e lc3tools_v12.zip ; then
    $CURL https://highered.mheducation.com/sites/dl/free/0072467509/104652/lc3tools_v12.zip
fi

if ! test -e LC301.exe ; then
    $CURL https://highered.mheducation.com/sites/dl/free/0072467509/104652/LC301.exe
fi
