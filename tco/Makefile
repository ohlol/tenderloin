BINARY = ../bin/tco
GOFILES = collector.go

.PHONY: all

all: $(BINARY)

$(BINARY): $(GOFILES)
	mkdir -p $(shell dirname $(BINARY))
	go build -o $(BINARY)
