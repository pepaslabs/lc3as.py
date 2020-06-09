#!/usr/bin/env python

# lc3as.py: an assembler for the LC-3.

# Copyright (c) 2020 Jason Pepas.
# This script is released under the terms of the MIT License.
# See https://opensource.org/licenses/MIT

# This assembler produces binary-identical output to the official assembler,
# which is available at:
# https://highered.mheducation.com/sites/0072467509/student_view0/lc-3_simulator.html

# The LC-3 is a fictitious machine described in the book "Introduction to
# Computing: From Bits and Gates to C and Beyond, 2nd Edition", by Patt and
# Patel.

# This script is compatible with Python 2 and Python 3.

import sys
import os

def usage(fd):
    exe = os.path.basename(sys.argv[0])
    fd.write('%s: an assembler for the LC-3 fictitious machine.\n' % exe)
    fd.write('\n')
    fd.write('Assemble foo.s (creates foo.bin, binary format):\n')
    fd.write("  %s foo.s\n" % exe)
    fd.write('\n')
    fd.write('Assemble standard input into standard output (binascii format):\n')
    fd.write("  cat foo.s | %s\n" % exe)
    fd.write("  cat foo.s | %s --binascii\n" % exe)
    fd.write('\n')
    fd.write('Assemble standard input into standard output (hex format):\n')
    fd.write("  cat foo.s | %s --hex\n" % exe)
    fd.write('\n')
    fd.write('Assemble standard input into standard output (forced binary format):\n')
    fd.write('Warning: this will spew garbage into your terminal, so redirect the output:\n')
    fd.write("  cat foo.s | %s --binary > foo.bin\n" % exe)
    fd.write("  cat foo.s | %s --binary | hexdump -C\n" % exe)
    fd.write('\n')
    fd.write('Stop after lexing foo.s into tokens (JSON output):\n')
    fd.write("  %s --lex foo.s | jq .\n" % exe)
    fd.write('\n')
    fd.write('Stop after parsing foo.s into statements (JSON output):\n')
    fd.write("  %s --parse foo.s | jq .\n" % exe)
    fd.write('\n')
    fd.write('Stop after generating the symbol table:\n')
    fd.write("  %s --symbols foo.s | column -t\n" % exe)
    fd.write('\n')
    fd.write('Assume input has already been parsed (JSON):\n')
    fd.write('(Useful for developing your own custom assembler syntax)\n')
    fd.write("  cat foo.s | %s --parse | %s --json-input --binary > foo.bin\n" % (exe, exe))
    fd.write("  ./my-custom-frontend foo.s | %s --json-input --binary > foo.bin\n" % exe)
    fd.write('\n')
    fd.write('Display this help message:\n')
    fd.write("  %s -h\n" % exe)
    fd.write("  %s --help\n" % exe)

import re
import json
import ast

class Obj(dict):
    """A dictionary with dot syntax."""
    def __getattr__(self, key):
        return self[key]
    def __setattr__(self, key, value):
        self[key] = value

# The LC-3 ISA, from "Appendix A", available at:
# http://highered.mheducation.com/sites/0072467509/student_view0/appendices_a__b__c__d____e.html
#
#       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# ADD  | 0   0   0   1 |     DR    |    SR1    | 0 | 0   0 |    SR2    |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# ADD  | 0   0   0   1 |     DR    |    SR1    | 1 |       imm5        |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# AND  | 0   1   0   1 |     DR    |    SR1    | 0 | 0   0 |    SR2    |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# AND  | 0   1   0   1 |     DR    |    SR1    | 1 |       imm5        |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# BR   | 0   0   0   0 | n | z | p |             PCoffset9             |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# JMP  | 1   1   0   0 | 0   0   0 |   BaseR   | 0   0   0   0   0   0 |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# JSR  | 0   1   0   0 | 1 |               PCoffset11                  |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# JSRR | 0   1   0   0 | 0 | 0   0 |   BaseR   | 0   0   0   0   0   0 |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# LD   | 0   0   1   0 |     DR    |             PCoffset9             |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# LDI  | 1   0   1   0 |     DR    |             PCoffset9             |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# LDR  | 0   1   1   0 |     DR    |   BaseR   |        offset6        |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# LEA  | 1   1   1   0 |     DR    |             PCoffset9             |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# NOT  | 1   0   0   1 |     DR    |     SR    | 1   1   1   1   1   1 |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# RET  | 1   1   0   0 | 0   0   0 | 1   1   1 | 0   0   0   0   0   0 |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# RTI  | 1   0   0   0 | 0   0   0   0   0   0   0   0   0   0   0   0 |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# ST   | 0   0   1   1 |     SR    |             PCoffset9             |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# STI  | 1   0   1   1 |     SR    |             PCoffset9             |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# STR  | 0   1   1   1 |     SR    |   BaseR   |        offset6        |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# TRAP | 1   1   1   1 | 0   0   0   0 |          trapvect8            |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
# N/A  | 1   1   0   1 |                                               |
#      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+

#
# The lexer.
#

token_patterns = [
    ('WS',         r'[\s,]+'),
    ('COMMENT',    r';.*'),
    ('HEX',        r'0?x[0-9a-fA-F]+'),
    ('NUMBER',     r'#?-?[0-9]+'),
    ('STRING',     r'"([^"\\]|\\.)*"'),
    ('OPCODE',     r'(?i)ADD|AND|BRn?z?p?|JMP|JSRR|JSR|LDI|LDR|LD|LEA|NOT|RET|RTI|STI|STR|ST|TRAP'),
    ('DIRECTIVE',  r'(?i)\.ORIG|\.END|\.FILL|\.BLKW|\.STRINGZ'),
    ('REGISTER',   r'[rR][0-6]'),
    ('LABEL',      r'[a-zA-Z0-9_-]+:'),
    ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_-]*'),
]

token_patterns = \
    [(typ, re.compile(patt, re.DOTALL)) for typ, patt in token_patterns]

def lex_line(line):
    """Turns the line of text into a list of tokens."""
    tokens = []
    i = 0
    while i < len(line):
        token = None
        for token_type, regex in token_patterns:
            m = regex.match(line, i)
            if m is None:
                continue
            text = m.group(0)
            token = Obj()
            token.type = 'TOKEN'
            token.token_type = token_type
            token.text = text
            if token_type == 'NUMBER':
                token.value = int(text.lstrip('#'), 10)
            elif token_type == 'HEX':
                token.value = int(text.lstrip('0x'), 16)
            elif token_type == 'STRING':
                # thanks to https://stackoverflow.com/a/1885211/558735
                token.value = ast.literal_eval(text)
            tokens.append(token)
            i += len(text)
            break
        if token is None:
            raise Exception("Cannot lex '%s'" % line.rstrip())
        continue
    return tokens

def lex(lines):
    """Lexes the list of source lines into lists of tokens."""
    return [lex_line(line) for line in lines]

#
# Individual operand parsers.
#

def parse_operand_label(token):
    """Attempts to parse a token as a LABEL."""
    failure = None
    if token.token_type == 'IDENTIFIER':
        operand = Obj()
        operand.type = 'OPERAND'
        operand.operand_type = 'LABEL'
        operand.name = token.text
        return operand
    return failure

def parse_operand_register(token):
    """Attempts to parse a token as a source, destination, or base register."""
    failure = None
    if token.token_type == 'REGISTER':
        operand = Obj()
        operand.type = 'OPERAND'
        operand.operand_type = 'REGISTER'
        operand.name = token.text.upper()
        operand.value = int(token.text[1:])
        return operand
    return failure

def parse_operand_int5(token):
    """Attempts to parse a token as a 5-bit signed immediate value."""
    failure = None
    if token.token_type in ['NUMBER', 'HEX']:
        operand = Obj()
        operand.type = 'OPERAND'
        operand.operand_type = 'IMMEDIATE'
        if token.value < -16 or token.value > 15:
            return failure
        operand.value = token.value
        return operand
    return failure

def parse_operand_int6(token):
    """Attempts to parse a token as a 6-bit signed immediate value."""
    failure = None
    if token.token_type in ['NUMBER', 'HEX']:
        operand = Obj()
        operand.type = 'OPERAND'
        operand.operand_type = 'IMMEDIATE'
        if token.value < -32 or token.value > 31:
            return failure
        operand.value = token.value
        return operand
    return failure

def parse_operand_uint8(token):
    """Attempts to parse a token as an 8-bit unsigned immediate value."""
    failure = None
    if token.token_type in ['NUMBER', 'HEX']:
        operand = Obj()
        operand.type = 'OPERAND'
        operand.operand_type = 'IMMEDIATE'
        if token.value < 0 or token.value > 255:
            return failure
        operand.value = token.value
        return operand
    return failure

#
# combinations of operand parsers.
#

def parse_operands_LABEL(tokens):
    """Attempts to parse operands of [LABEL]."""
    failure = None
    if len(tokens) != 1:
        return failure
    op1 = parse_operand_label(tokens[0])
    if op1 is None:
        return failure
    return [op1]

def parse_operands_BaseR(tokens):
    """Attempts to parse operands of [BaseR]."""
    failure = None
    if len(tokens) != 1:
        return failure
    op1 = parse_operand_register(tokens[0])
    if op1 is None:
        return failure
    return [op1]

def parse_operands_DR_LABEL(tokens):
    """Attempts to parse operands of [DR, LABEL]."""
    failure = None
    if len(tokens) != 2:
        return failure
    op1 = parse_operand_register(tokens[0])
    if op1 is None:
        return failure
    op2 = parse_operand_label(tokens[1])
    if op2 is None:
        return failure
    return [op1, op2]

def parse_operands_SR_LABEL(tokens):
    return parse_operands_DR_LABEL(tokens)

def parse_operands_DR_SR(tokens):
    """Attempts to parse operands of [DR, SR]."""
    failure = None
    if len(tokens) != 2:
        return failure
    op1 = parse_operand_register(tokens[0])
    if op1 is None:
        return failure
    op2 = parse_operand_register(tokens[1])
    if op2 is None:
        return failure
    return [op1, op2]

def parse_operands_DR_SR1_SR2(tokens):
    """Attempts to parse operands of [DR, SR1, SR2]."""
    failure = None
    if len(tokens) != 3:
        return failure
    op1 = parse_operand_register(tokens[0])
    if op1 is None:
        return failure
    op2 = parse_operand_register(tokens[1])
    if op2 is None:
        return failure
    op3 = parse_operand_register(tokens[2])
    if op3 is None:
        return failure
    return [op1, op2, op3]

def parse_operands_DR_SR1_imm5(tokens):
    """Attempts to parse operands of [DR, SR1, imm5]."""
    failure = None
    if len(tokens) != 3:
        return failure
    op1 = parse_operand_register(tokens[0])
    if op1 is None:
        return failure
    op2 = parse_operand_register(tokens[1])
    if op2 is None:
        return failure
    op3 = parse_operand_int5(tokens[2])
    if op3 is None:
        return failure
    return [op1, op2, op3]

def parse_operands_DR_BaseR_offset6(tokens):
    """Attempts to parse operands of [DR, BaseR, offset6]."""
    failure = None
    if len(tokens) != 3:
        return failure
    op1 = parse_operand_register(tokens[0])
    if op1 is None:
        return failure
    op2 = parse_operand_register(tokens[1])
    if op2 is None:
        return failure
    op3 = parse_operand_int6(tokens[2])
    if op3 is None:
        return failure
    return [op1, op2, op3]

def parse_operands_SR_BaseR_offset6(tokens):
    return parse_operands_DR_BaseR_offset6(tokens)

def parse_operands_trapvector8(tokens):
    """Attempts to parse operands of [trapvect8]."""
    failure = None
    if len(tokens) != 1:
        return failure
    op1 = parse_operand_uint8(tokens[0])
    if op1 is None:
        return failure
    return [op1]

#
# instruction parsers.
#

def parse_ADD_ins(tokens):
    """Attempts to parse an ADD instruction."""
    failure = None
    assert len(tokens) > 0
    if tokens[0].text.upper() != 'ADD':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'ADD'
    operands = parse_operands_DR_SR1_SR2(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    operands = parse_operands_DR_SR1_imm5(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_AND_ins(tokens):
    """Attempts to parse an AND instruction."""
    failure = None
    assert len(tokens) > 0
    if tokens[0].text.upper() != 'AND':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'AND'
    operands = parse_operands_DR_SR1_SR2(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    operands = parse_operands_DR_SR1_imm5(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_BR_ins(tokens):
    """Attempts to parse a BR instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper()[:2] != 'BR':
        return failure
    if op.lower()[2:] not in ['', 'n', 'z', 'p', 'np', 'nz', 'zp', 'nzp']:
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = op.upper()[:2]
    if len(op) > 2:
        statement.instruction += op.lower()[2:]
    operands = parse_operands_LABEL(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_JMP_ins(tokens):
    """Attempts to parse a JMP instruction."""
    failure = None
    assert len(tokens) > 0
    if tokens[0].text.upper() != 'JMP':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'JMP'
    operands = parse_operands_BaseR(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_RET_ins(tokens):
    """Attempts to parse a RET instruction."""
    failure = None
    assert len(tokens) > 0
    if tokens[0].text.upper() != 'RET':
        return failure
    if len(tokens) > 1:
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'RET'
    return statement

def parse_JSR_ins(tokens):
    """Attempts to parse a JSR instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'JSR':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'JSR'
    operands = parse_operands_LABEL(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_JSRR_ins(tokens):
    """Attempts to parse a JSRR instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'JSRR':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'JSRR'
    operands = parse_operands_BaseR(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_LD_ins(tokens):
    """Attempts to parse an LD instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'LD':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'LD'
    operands = parse_operands_DR_LABEL(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_LDI_ins(tokens):
    """Attempts to parse a LDI instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'LDI':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'LDI'
    operands = parse_operands_DR_LABEL(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_LDR_ins(tokens):
    """Attempts to parse a LDR instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'LDR':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'LDR'
    operands = parse_operands_DR_BaseR_offset6(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_LEA_ins(tokens):
    """Attempts to parse a LEA instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'LEA':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'LEA'
    operands = parse_operands_DR_LABEL(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_NOT_ins(tokens):
    """Attempts to parse a NOT instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'NOT':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'NOT'
    operands = parse_operands_DR_SR(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_RTI_ins(tokens):
    """Attempts to parse a RTI instruction."""
    failure = None
    assert len(tokens) > 0
    if tokens[0].text.upper() != 'RTI':
        return failure
    if len(tokens) > 1:
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'RTI'
    return statement

def parse_ST_ins(tokens):
    """Attempts to parse a ST instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'ST':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'ST'
    operands = parse_operands_SR_LABEL(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_STI_ins(tokens):
    """Attempts to parse a STI instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'STI':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'STI'
    operands = parse_operands_SR_LABEL(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_STR_ins(tokens):
    """Attempts to parse a STR instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'STR':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'STR'
    operands = parse_operands_SR_BaseR_offset6(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

def parse_TRAP_ins(tokens):
    """Attempts to parse a TRAP instruction."""
    failure = None
    assert len(tokens) > 0
    token1 = tokens[0]
    op = token1.text
    if op.upper() != 'TRAP':
        return failure
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'INSTRUCTION'
    statement.instruction = 'TRAP'
    operands = parse_operands_trapvector8(tokens[1:])
    if operands:
        statement.operands = operands
        return statement
    return failure

ins_parsers = [
    parse_ADD_ins,
    parse_AND_ins,
    parse_BR_ins,
    parse_JMP_ins,
    parse_RET_ins,
    parse_JSR_ins,
    parse_JSRR_ins,
    parse_LD_ins,
    parse_LDI_ins,
    parse_LDR_ins,
    parse_LEA_ins,
    parse_NOT_ins,
    parse_RET_ins,
    parse_RTI_ins,
    parse_ST_ins,
    parse_STI_ins,
    parse_STR_ins,
    parse_TRAP_ins,
]

#
# statement parsers.
#

def parse_instruction_statement(tokens):
    """Attempts to parse a line of tokens as an instruction statement."""
    failure = None
    assert len(tokens) >= 1
    token1 = tokens[0]
    if token1.token_type != 'OPCODE':
        return failure
    statement = None
    for fn in ins_parsers:
        statement = fn(tokens)
        if statement is not None:
            break
        else:
            continue
    if statement is None:
        return failure
    return statement

def parse_directive_statement(tokens):
    """Attempts to parse a line of tokens as a directive statement."""
    failure = None
    statement = Obj()
    statement.type = 'STATEMENT'
    statement.statement_type = 'DIRECTIVE'
    if len(tokens) == 1:
        token1 = tokens[0]
        if token1.token_type == 'LABEL':
            statement.directive_type = 'LABEL'
            statement.label_name = token1.text.rstrip(':')
            return statement
        elif token1.token_type == 'DIRECTIVE' and token1.text.upper() == '.END':
            statement.directive_type = 'END'
            return statement
        elif token1.token_type == 'IDENTIFIER':
            # The textbook allows labels which don't end in ':'.  If we see
            # an identifier on a line by itself, assume it is a label.
            statement.directive_type = 'LABEL'
            statement.label_name = token1.text.rstrip(':')
            return statement
    elif len(tokens) == 2:
        token1 = tokens[0]
        token2 = tokens[1]
        if token1.token_type == 'DIRECTIVE':
            text = token1.text.upper()
            if text == '.ORIG' and token2.token_type == 'HEX':
                statement.directive_type = 'ORIG'
                statement.address = token2.value
                return statement
            elif text == '.FILL':
                statement.directive_type = 'FILL'
                if token2.token_type in ['NUMBER', 'HEX']:
                    statement.value = token2.value
                    return statement
                elif token2.token_type == 'IDENTIFIER':
                    statement.label = token2.text
                    return statement
            elif text == '.BLKW':
                statement.directive_type = 'BLKW'
                if token2.token_type in ['NUMBER', 'HEX']:
                    statement.size = token2.value
                    return statement
            elif text == '.STRINGZ':
                statement.directive_type = 'STRINGZ'
                if token2.token_type == 'STRING':
                    statement.value = token2.value
                    return statement
    return failure

statement_parsers = [
    parse_directive_statement,
    parse_instruction_statement,
]

#
# The parser.
#

def filter_tokens(tokens):
    """Filters out any whitespace and comment tokens."""
    return [token for token in tokens if token.token_type not in ['WS', 'COMMENT']]

def parse_line(tokens, linenum):
    """Parses the line of tokens into a list of statements.
    Returns None on empty line.
    Throws on parse error.
    Note: labels are split off and processed as standalone statements."""
    tokens = filter_tokens(tokens)
    if len(tokens) == 0:
        return []
    elif len(tokens) > 1 and tokens[0].token_type == 'LABEL':
        return parse_line(tokens[:1], linenum) + parse_line(tokens[1:], linenum)
    elif len(tokens) > 1 \
        and tokens[0].token_type == 'IDENTIFIER' \
        and tokens[1].token_type in ['OPCODE', 'DIRECTIVE']:
        # The textbook allows labels which don't end in ':'.  If the first
        # token is an identifier and the second token is an opcode or a
        # directive, assume the identifier is a label.
        return parse_line(tokens[:1], linenum) + parse_line(tokens[1:], linenum)
    for parser_fn in statement_parsers:
        statement = parser_fn(tokens)
        if statement is not None:
            break
        else:
            continue
    if statement is None:
        raise Exception("Line %s: cannot parse '%s'" % (linenum, tokens))
    return [statement]

def parse(lexed_lines):
    """Parses the lexed lines of tokens into statements."""
    statements = []
    for i, tokens in enumerate(lexed_lines):
        linenum = i + 1
        line_statements = parse_line(tokens, linenum)
        if line_statements is None:
            continue
        else:
            statements += line_statements
            continue
    return statements

#
# The assembler.
#

def size_of_ins(statement):
    """Returns the size (in words) of the instruction."""
    # Note: the LC-3 is word-addressable, not byte-addressable, so a two-byte
    # instruction has a size of 1, not 2.
    # There is a variant called the LC-3b which is byte-addressable.
    if statement.statement_type == 'INSTRUCTION':
        # All LC-3 instructions are 2 bytes (size of 1).
        return 1
    elif statement.statement_type == 'DIRECTIVE':
        if statement.directive_type == 'FILL':
            return 1
        elif statement.directive_type == 'BLKW':
            return statement.size
        elif statement.directive_type == 'STRINGZ':
            byte_count = len(statement.value) + 1
            word_count = int(byte_count / 2)
            return word_count
    return None

def make_symbol_table(statements):
    """Generates the symbol table."""
    symbol_table = {}
    location_counter = None
    # first, find the .ORIG directive.
    for statement in statements:
        if statement.statement_type == 'DIRECTIVE' and statement.directive_type == 'ORIG':
            location_counter = statement.address
            break
        else:
            continue
    if location_counter is None:
        raise Exception("Couldn't find a .ORIG directive.")
    # now create the symbol table.
    for statement in statements:
        if statement.statement_type == 'DIRECTIVE' and statement.directive_type == 'LABEL':
            label_name = statement.label_name
            if label_name in symbol_table:
                raise Exception("Label '%s' already in symbol table." % label_name)
            symbol_table[label_name] = location_counter
            continue
        else:
            size = size_of_ins(statement)
            if size is not None:
                location_counter += size
            continue
    return symbol_table

#
# Machine instruction fragment helpers.
#

def lookup_label(label, symtable):
    """Label lookup with user-friendly exception."""
    if label not in symtable:
        raise Exception("Undefined label '%s'" % label)
    return symtable[label]

def generate_imm5(value):
    """Returns the 5-bit two's complement representation of the number."""
    if value < 0:
        # the sign bit needs to be bit number 5.
        return 0x1 << 4 | (0b1111 & value)
    else:
        return value

def generate_offset6(value):
    """Returns the 6-bit two's complement representation of the number."""
    if value < 0:
        # the sign bit needs to be bit number 6.
        return 0x1 << 5 | (0b11111 & value)
    else:
        return value

def generate_pcoffset9(label, symtable, pc):
    """Turns a label into a 9-bit two's complement signed offset."""
    address = lookup_label(label, symtable)
    pcoffset = address - pc
    if pcoffset < -256 or pcoffset > 255:
        raise Exception(
            "Jump from PC (%s) to label %s (%s) does not fit within PCoffset9." \
                % (pc, label, address)
        )
    if pcoffset < 0:
        # the sign bit needs to be bit number 9.
        return 0x1 << 8 | (0b11111111 & pcoffset)
    else:
        return pcoffset

def generate_pcoffset11(label, symtable, pc):
    """Turns a label into an 11-bit two's complement signed offset."""
    address = lookup_label(label, symtable)
    pcoffset = address - pc
    if pcoffset < -1024 or pcoffset > 1023:
        raise Exception(
            "Jump from PC (%s) to label %s (%s) does not fit within PCoffset11." \
                % (pc, label, address)
        )
    if pcoffset < 0:
        # the sign bit needs to be bit number 11.
        return 0x1 << 10 | (0b1111111111 & pcoffset)
    else:
        return pcoffset

#
# Reusable machine instruction generators.
#

opcodes = {
    'BR':    0x0,
    'BRn':   0x0,
    'BRz':   0x0,
    'BRp':   0x0,
    'BRnz':  0x0,
    'BRnp':  0x0,
    'BRzp':  0x0,
    'BRnzp': 0x0,
    'ADD':   0x1,
    'LD':    0x2,
    'ST':    0x3,
    'JSR':   0x4,
    'JSRR':  0x4,
    'AND':   0x5,
    'LDR':   0x6,
    'STR':   0x7,
    'RTI':   0x8,
    'NOT':   0x9,
    'LDI':   0xA,
    'STI':   0xB,
    'JMP':   0xC,
    'RET':   0xC,
    'LEA':   0xE,
    'TRAP':  0xF,
}

def generate_bmins_DR_SR1_SR2(statement):
    """Generates a binary machine instruction of the [DR, SR1, SR2] format."""
    #  15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    # +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # | X   X   X   X |     DR    |    SR1    | 0 | 0   0 |    SR2    |
    # +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    opnds = statement.operands
    dr = opnds[0].value
    sr1 = opnds[1].value
    sr2 = opnds[2].value
    bmins = opcode << 12 | dr << 9 | sr1 << 6 | sr2 << 0
    return bmins

def generate_bmins_DR_SR1_imm5(statement):
    """Generates a binary machine instruction of the [DR, SR1, imm5] format."""
    #  15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    # +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # | X   X   X   X |     DR    |    SR1    | 1 |       imm5        |
    # +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    opnds = statement.operands
    dr = opnds[0].value
    sr1 = opnds[1].value
    imm5 = generate_imm5(opnds[2].value)
    bmins = opcode << 12 | dr << 9 | sr1 << 6 | 0b1 << 5 | imm5 << 0
    return bmins

def generate_bmins_DR_PCoffset9(statement, symtable, pc):
    """Generates a binary machine instruction of the [DR, PCoffset9] format."""
    #  15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    # +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # | X   X   X   X |     DR    |             PCoffset9             |
    # +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    opnds = statement.operands
    dr = opnds[0].value
    label = opnds[1].name
    pcoffset9 = generate_pcoffset9(label, symtable, pc)
    bmins = opcode << 12 | dr << 9 | pcoffset9 << 0
    return bmins

def generate_bmins_SR_PCoffset9(statement, symtable, pc):
    """Generates a binary machine instruction of the [SR, PCoffset9] format."""
    return generate_bmins_DR_PCoffset9(statement, symtable, pc)

def generate_bmins_DR_BaseR_offset6(statement):
    #  15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    # +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # | X   X   X   X |     DR    |   BaseR   |        offset6        |
    # +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    opnds = statement.operands
    dr = opnds[0].value
    baser = opnds[1].value
    offset6 = generate_offset6(opnds[2].value)
    bmins = opcode << 12 | dr << 9 | baser << 6 | offset6 << 0
    return bmins

def generate_bmins_SR_BaseR_offset6(statement):
    """Generates a binary machine instruction of the [SR, BaseR, offset6] format."""
    return generate_bmins_DR_BaseR_offset6(statement)

#
# Generate machine instructions.
#

def generate_ADD(statement):
    """Generates an ADD binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # ADD  | 0   0   0   1 |     DR    |    SR1    | 0 | 0   0 |    SR2    |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # ADD  | 0   0   0   1 |     DR    |    SR1    | 1 |       imm5        |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    if statement.operands[2].operand_type == 'REGISTER':
        return generate_bmins_DR_SR1_SR2(statement)
    elif statement.operands[2].operand_type == 'IMMEDIATE':
        return generate_bmins_DR_SR1_imm5(statement)
    else:
        assert False

def generate_AND(statement):
    """Generates an AND binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # AND  | 0   1   0   1 |     DR    |    SR1    | 0 | 0   0 |    SR2    |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # AND  | 0   1   0   1 |     DR    |    SR1    | 1 |       imm5        |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    if statement.operands[2].operand_type == 'REGISTER':
        return generate_bmins_DR_SR1_SR2(statement)
    elif statement.operands[2].operand_type == 'IMMEDIATE':
        return generate_bmins_DR_SR1_imm5(statement)
    else:
        assert False

def generate_BR(statement, symtable, pc):
    """Generates a BR binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # BR   | 0   0   0   0 | n | z | p |             PCoffset9             |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    label = statement.operands[0].name
    pcoffset9 = generate_pcoffset9(label, symtable, pc)
    n = 0x1 if 'n' in statement.instruction else 0x0
    z = 0x1 if 'z' in statement.instruction else 0x0
    p = 0x1 if 'p' in statement.instruction else 0x0
    # a naked BR should be interpreted as a BRnzp.
    if n == 0 and z == 0 and p == 0:
        n = 1; z = 1; p = 1
    bmins = opcode << 12 | n << 11 | z << 10 | p << 9 | pcoffset9 << 0
    return bmins

def generate_JMP(statement):
    """Generates a JMP binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # JMP  | 1   1   0   0 | 0   0   0 |   BaseR   | 0   0   0   0   0   0 |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    baser = statement.operands[0].value
    bmins = opcode << 12 | baser << 6
    return bmins

def generate_JSR(statement, symtable, pc):
    """Generates a JSR binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # JSR  | 0   1   0   0 | 1 |               PCoffset11                  |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    label = statement.operands[0].name
    pcoffset11 = generate_pcoffset11(label, symtable, pc)
    bmins = opcode << 12 | 0b1 << 11 | pcoffset11 << 0
    return bmins

def generate_JSRR(statement):
    """Generates a JSRR binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # JSRR | 0   1   0   0 | 0 | 0   0 |   BaseR   | 0   0   0   0   0   0 |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    baser = statement.operands[0].value
    bmins = opcode << 12 | baser << 6
    return bmins

def generate_LD(statement, symtable, pc):
    """Generates an LD binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # LD   | 0   0   1   0 |     DR    |             PCoffset9             |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    return generate_bmins_DR_PCoffset9(statement, symtable, pc)

def generate_LDI(statement, symtable, pc):
    """Generates an LDI binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # LDI  | 1   0   1   0 |     DR    |             PCoffset9             |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    return generate_bmins_DR_PCoffset9(statement, symtable, pc)

def generate_LDR(statement):
    """Generates an LDR binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # LDR  | 0   1   1   0 |     DR    |   BaseR   |        offset6        |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    return generate_bmins_DR_BaseR_offset6(statement)

def generate_LEA(statement, symtable, pc):
    """Generates an LEA binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # LEA  | 1   1   1   0 |     DR    |             PCoffset9             |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    return generate_bmins_DR_PCoffset9(statement, symtable, pc)

def generate_NOT(statement):
    """Generates a NOT binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # NOT  | 1   0   0   1 |     DR    |     SR    | 1   1   1   1   1   1 |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    opnds = statement.operands
    dr = opnds[0].value
    sr = opnds[1].value
    bmins = opcode << 12 | dr << 9 | sr << 6 | 0b111111 << 0
    return bmins

def generate_RET(statement):
    """Generates a RET binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # RET  | 1   1   0   0 | 0   0   0 | 1   1   1 | 0   0   0   0   0   0 |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    bmins = opcode << 12 | 0b111 << 6
    return bmins

def generate_RTI():
    """Generates a RTI binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # RTI  | 1   0   0   0 | 0   0   0   0   0   0   0   0   0   0   0   0 |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    return 0x1 << 15

def generate_ST(statement, symtable, pc):
    """Generates a ST binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # ST   | 0   0   1   1 |     SR    |             PCoffset9             |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    return generate_bmins_SR_PCoffset9(statement, symtable, pc)

def generate_STI(statement, symtable, pc):
    """Generates a STI binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # STI  | 1   0   1   1 |     SR    |             PCoffset9             |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    return generate_bmins_DR_PCoffset9(statement, symtable, pc)

def generate_STR(statement):
    """Generates a STR binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # STR  | 0   1   1   1 |     SR    |   BaseR   |        offset6        |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    return generate_bmins_SR_BaseR_offset6(statement)

def generate_TRAP(statement):
    """Generates a TRAP binary machine instruction."""
    #       15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    # TRAP | 1   1   1   1 | 0   0   0   0 |          trapvect8            |
    #      +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    opcode = opcodes[statement.instruction]
    trapvect8 = statement.operands[0].value
    bmins = opcode << 12 | trapvect8 << 0
    return bmins

def assemble_statement(statement, symtable, pc):
    """Turns a statement into a list of binary machine instructions."""
    if statement.statement_type == 'INSTRUCTION':
        insname = statement.instruction
        if insname == 'ADD':
            bmin = generate_ADD(statement)
        elif insname == 'AND':
            bmin = generate_AND(statement)
        elif insname.startswith('BR'):
            bmin = generate_BR(statement, symtable, pc)
        elif insname == 'JMP':
            bmin = generate_JMP(statement)
        elif insname == 'JSR':
            bmin = generate_JSR(statement, symtable, pc)
        elif insname == 'JSRR':
            bmin = generate_JSRR(statement)
        elif insname == 'LD':
            bmin = generate_LD(statement, symtable, pc)
        elif insname == 'LDI':
            bmin = generate_LDI(statement, symtable, pc)
        elif insname == 'LDR':
            bmin = generate_LDR(statement)
        elif insname == 'LEA':
            bmin = generate_LEA(statement, symtable, pc)
        elif insname == 'NOT':
            bmin = generate_NOT(statement)
        elif insname == 'RET':
            bmin = generate_RET(statement)
        elif insname == 'RTI':
            bmin = generate_RTI()
        elif insname == 'ST':
            bmin = generate_ST(statement, symtable, pc)
        elif insname == 'STI':
            bmin = generate_STI(statement, symtable, pc)
        elif insname == 'STR':
            bmin = generate_STR(statement)
        elif insname == 'TRAP':
            bmin = generate_TRAP(statement)
        return [bmin]
    elif statement.statement_type == 'DIRECTIVE':
        if statement.directive_type in ['LABEL', 'ORIG', 'END']:
            return None
        # "instructions" which are actually just data.
        if statement.directive_type == 'FILL':
            return [statement.value]
        elif statement.directive_type == 'BLKW':
            bmins = []
            for _ in range(len(statement.value)):
                bmins.append(0)
                return bmins
        elif statement.directive_type == 'STRINGZ':
            bmins = []
            chars = statement.value
            i = 0
            # pack two chars into each "instruction".
            while len(chars) - i >= 2:
                bmin = ord(chars[i]) << 8 | ord(chars[i+1]) << 0
                bmins.append(bmin)
                i += 2
            if i == 0:
                # we had an even number of chars.  append the terminating NULL.
                bmins.append(0)
            elif i == 1:
                # we had an odd number of chars.  append the last straggler
                # along with a terminating NULL.
                bmin = ord(chars[i]) << 8 | 0x0 << 0
                bmins.append(bmin)
            return bmins
    raise Exception("Don't know how to assemble: %s" % statement)

def assemble(statements, symtable):
    """Turns the statements into binary machine instructions."""
    machine_instructions = []
    # first, find the .ORIG directive.
    location_counter = None
    for statement in statements:
        if statement.statement_type == 'DIRECTIVE' and statement.directive_type == 'ORIG':
            location_counter = statement.address
            # the first two bytes of the binary output format is the .ORIG address.
            machine_instructions.append(location_counter)
            break
        else:
            continue
    assert location_counter is not None
    # now assemble the binary machine instructions.
    for statement in statements:
        # Note: any PC offsets are relative to the program counter, which has
        # already been incremented by the time the instruction executes, which
        # is why program counter and location counter differ by 1 at the time
        # of offset calculation.
        program_counter = location_counter + 1
        bmins = assemble_statement(statement, symtable, program_counter)
        if bmins is None:
            continue
        machine_instructions += bmins
        location_counter += len(bmins)
        continue
    return machine_instructions

#
# The executor.
#

def parse_args():
    """Parses the command-line arguments."""
    job = Obj()
    job.mode = 'MODE_ALL'
    job.infile = None
    job.json_input = False
    job.output_format = None
    for arg in sys.argv[1:]:
        if arg in ['-h', '--help']:
            job.mode = 'MODE_HELP'
        elif arg == '--lex':
            job.mode = 'MODE_LEX'
        elif arg == '--parse':
            job.mode = 'MODE_PARSE'
        elif arg == '--symbols':
            job.mode = 'MODE_SYMBOLS'
        elif arg == '--hex':
            job.output_format = 'HEX'
        elif arg == '--binascii':
            job.output_format = 'BINASCII'
        elif arg == '--binary':
            job.output_format = 'BINARY'
        elif arg == '--json-input':
            job.json_input = True
        else:
            job.infile = arg

    if job.infile is not None:
        if job.output_format is None:
            job.output_format = 'BINARY'
            job.outfile = job.infile.rsplit('.', 1)[0] + '.bin'
        elif job.output_format == 'BINARY':
            job.outfile = job.infile.rsplit('.', 1)[0] + '.bin'
        else:
            job.outfile = None
    else:
        job.outfile = None
        if job.output_format is None:
            job.output_format = 'BINASCII'

    return job

def run_job(job):
    """Assemble the input according to the command-line parameters."""
    if job.mode == 'MODE_HELP':
        usage(sys.stdout)
        return 0
    
    if job.infile is None and sys.stdin.isatty():
        # if the user didn't specify an input file, but also hasn't directed a
        # file or pipe into stdin, they probably don't know what they are doing.
        # show usage and bail.
        usage(sys.stderr)
        return 1

    if job.infile is None:
        fd = sys.stdin
    else:
        fd = open(job.infile, 'r')
    text = fd.read()
    if fd is not sys.stdin:
        fd.close()

    if job.json_input:
        # Skip lexing and parsing and injest pre-parsed JSON input.
        # Useful for writing your own custom assembly syntax.
        js_statements = json.loads(text)
        statements = []
        for js_dict in js_statements:
            obj = Obj(js_dict)
            if 'operands' in obj:
                opands = []
                for js_opand in obj.operands:
                    opand = Obj(js_opand)
                    opands.append(opand)
                    continue
                obj.operands = opands
            statements.append(obj)
            continue
    else:
        lines = [line.rstrip() for line in text.splitlines()]

        lexed_lines = lex(lines)
        if job.mode == 'MODE_LEX':
            js = json.dumps(lexed_lines)
            sys.stdout.write(js)
            sys.stdout.write('\n')
            return 0

        statements = parse(lexed_lines)
        if job.mode == 'MODE_PARSE':
            js = json.dumps(statements)
            sys.stdout.write(js)
            sys.stdout.write('\n')
            return 0

    # pass 1: generate the symbol table.
    symbol_table = make_symbol_table(statements)
    if job.mode == 'MODE_SYMBOLS':
        def key_fn(pair):
            k, v = pair
            return v
        sorted_by_address = sorted(symbol_table.items(), key=key_fn)
        for k, v in sorted_by_address:
            sys.stdout.write("%s %s\n" % (k, hex(v)))
            continue
        return 0

    # pass 2: assemble the machine instructions.
    machine_instructions = assemble(statements, symbol_table)

    # output.
    if job.outfile:
        fd = open(job.outfile, 'wb')
    else:
        fd = sys.stdout
    if job.output_format == 'BINASCII':
        for bmin in machine_instructions:
            fd.write(format(bmin, '016b') + '\n')
    elif job.output_format == 'HEX':
        for bmin in machine_instructions:
            fd.write('0x' + format(bmin, '04X') + '\n')
    elif job.output_format == 'BINARY':
        for bmin in machine_instructions:
            byte1 = bmin >> 8
            byte2 = bmin & 0xFF
            fd.write(bytearray([byte1, byte2]))
    else:
        assert False
    if fd is not sys.stdin:
        fd.close()
    return 0

if __name__ == '__main__':
    job = parse_args()
    ret = run_job(job)
    sys.exit(ret)
