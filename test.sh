#!/bin/bash

# test the assembler by comparing its output to the official assembler's output.

# the official assembler is available at:
# https://highered.mheducation.com/sites/0072467509/student_view0/lc-3_simulator.html

set -e -o pipefail
#set -x

cd examples
for f in test*.asm halt.asm hello.asm ; do
    echo -e "\ntesting $f"

    obj=$(basename $f .asm).obj
    expected=/tmp/expected.obj
    sut=/tmp/sut.obj
    rm -f $expected $sut

    lc3as $f
    mv $obj $expected

    python3 ../lc3as.py $f
    mv $obj $sut

    if ! diff -q $expected $sut
    then
        echo "Error: output does not match official assembler output"
        echo -e "\n${expected} (correct):"
        cat $expected | hexdump -C | tee ${expected}.hex
        echo -e "\n${sut} (incorrect):"
        cat $sut | hexdump -C | tee ${sut}.hex
        echo -e "\ndifferences:"
        diff -urN --color=auto ${sut}.hex ${expected}.hex
        exit 1
    fi
done
