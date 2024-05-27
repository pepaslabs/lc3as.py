#!/bin/bash

# test the assembler by comparing its output to the official assembler's output.

# the official assembler is available at:
# https://highered.mheducation.com/sites/0072467509/student_view0/lc-3_simulator.html

set -e -o pipefail

PYTHON=`which python3`

cd examples
for f in test*.asm
do
    echo -e "\ntesting $f"
    lc3as $f
    obj=$( basename $f .asm).obj
    $PYTHON ../lc3as.py $f
    bin=$( basename $f .asm).bin
    if ! diff -q $obj $bin
    then
        echo "Error: output does not match official assembler output"
        echo -e "\n${obj} (correct):"
        cat $obj | hexdump -C | tee ${obj}.hex
        echo -e "\n${bin} (incorrect):"
        cat $bin | hexdump -C | tee ${bin}.hex
        echo -e "\ndifferences:"
        diff -urN --color=auto ${bin}.hex ${obj}.hex
        exit 1
    fi
done
