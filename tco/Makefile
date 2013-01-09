BINARY = ../bin/tco
GOFILES = collector.go

.PHONY: all $(BINARY)

all: tco

tco: $(GOFILES) $(BINARY)
	@echo $(GOPATH)
	go build -o $(BINARY)
