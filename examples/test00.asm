; basic test of syntax.
; this is a comment
 ; comment with leading space
.ORIG x3000
LABEL1:
 LABEL2:
LABEL3: ; comment
LABEL4:;comment
ADD R1, R2, #0
ADD R1,R2,#0
ADD R1,R2,#0;comment
LABEL5: ADD R1, R2, #0
LABEL6:ADD R1,R2,#0
LABEL7:ADD R1,R2,#0;comment
.END
