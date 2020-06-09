all: test clean

test: testpy2 testpy3

testpy2:
	./test.sh python2

testpy3:
	./test.sh python3

clean:
	rm -f examples/*.bin
	rm -f examples/*.obj
	rm -f examples/*.sym
	rm -f examples/*.hex

.PHONY: all test testpy2 testpy3 clean
