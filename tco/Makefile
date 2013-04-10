BINARY = ../bin/tco
GOFILES = collector.go

.PHONY: all $(BINARY)

all: tco

tco: $(GOFILES) $(BINARY)
	mkdir -p $(shell dirname $(BINARY))
	go build -o $(BINARY)
