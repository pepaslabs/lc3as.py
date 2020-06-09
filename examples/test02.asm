; this is a basic test of whether the assembler can parse all of
; the instructions / formats.

.ORIG x3000

ADD R1, R2, R3
ADD R1, R2, #-1
ADD R1, R2, xF

foo: ADD R1, R2, R3

AND R1, R2, R3
AND R1, R2, #-1
AND R1, R2, xF

BR foo
BRn foo
BRz foo
BRp foo
BRnz foo
BRnp foo
BRzp foo
BRnzp foo

JMP R1

RET

JSR foo

JSRR R1

LD R1, foo

LDI R1, foo

LDR R1, R2, #3
LDR R1, R2, #-8
LDR R1, R2, x1F

LEA R1, foo

NOT R1, R2

RTI

ST R1, foo

STI R1, foo

STR R1, R2, #1
STR R1, R2, #-7
STR R1, R2, x1A

TRAP #129
TRAP xFF

.END
