all: test clean

test:
	./test.sh

clean:
	cd examples && make clean

.PHONY: all test clean
