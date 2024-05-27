all: test clean

test:
	./test.sh

clean:
	rm -f examples/*.bin
	rm -f examples/*.obj
	rm -f examples/*.sym
	rm -f examples/*.hex

.PHONY: all test clean
