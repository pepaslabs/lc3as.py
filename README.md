# lc3as.py

An assembler for the LC-3 fictitious computer.

```
$ ./lc3as.py --help
lc3as.py: an assembler for the LC-3 ficticious machine.

Assemble foo.s (creates foo.bin, binary format):
  lc3as.py foo.s

Assemble standard input into standard output (binascii format):
  cat foo.s | lc3as.py
  cat foo.s | lc3as.py --binascii

Assemble standard input into standard output (hex format):
  cat foo.s | lc3as.py --hex

Assemble standard input into standard output (forced binary format):
Warning: this will spew garbage into your terminal, so redirect the output:
  cat foo.s | lc3as.py --binary > foo.bin
  cat foo.s | lc3as.py --binary | hexdump -C

Stop after lexing foo.s into tokens (JSON output):
  lc3as.py --lex foo.s | jq .

Stop after parsing foo.s into statements (JSON output):
  lc3as.py --parse foo.s | jq .

Stop after generating the symbol table:
  lc3as.py --symbols foo.s | column -t

Assume input has already been parsed (JSON):
(Useful for developing your own custom assembler syntax)
  ./my-custom-frontend foo.s | lc3as.py --json-input --binary > foo.bin
  lc3as.py --parse foo.s | lc3as.py --json-input --binary > foo.bin

Display this help message:
  lc3as.py -h
  lc3as.py --help
```
