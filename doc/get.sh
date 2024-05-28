#!/bin/bash

set -e

# See also https://highered.mheducation.com/sites/0072467509/

CURL='curl --fail --remote-name --location'

if ! test -e LC3_unix.pdf ; then
    $CURL https://highered.mheducation.com/sites/dl/free/0072467509/104652/LC3_unix.pdf
fi

if ! test -e LC3WinGuide.pdf ; then
    $CURL https://highered.mheducation.com/sites/dl/free/0072467509/104652/LC3WinGuide.pdf
fi

if ! test -e pat67509_appa.pdf ; then
    $CURL https://highered.mheducation.com/sites/dl/free/0072467509/104691/pat67509_appa.pdf
fi

if ! test -e Lecture_10-310h.pdf ; then
    $CURL https://www.cs.utexas.edu/users/fussell/cs310h/lectures/Lecture_10-310h.pdf
fi

if ! test -e LC3-AssemblyManualAndExamples.pdf ; then
    $CURL https://people.cs.georgetown.edu/~squier/Teaching/HardwareFundamentals/LC3-trunk/docs/LC3-AssemblyManualAndExamples.pdf
fi

# This is LC-2, but high-quality docs:
if ! test -e lc2.pdf ; then
    $CURL https://www.cs.utexas.edu/users/fussell/courses/cs310h/simulator/lc2.pdf
fi

