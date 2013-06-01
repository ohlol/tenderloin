BINARY = ../bin/tl
GOFILES = \
	metrics.go \
	poller.go \
	server.go \
	web.go

.PHONY: all

all: $(BINARY)

$(BINARY): $(GOFILES)
	mkdir -p $(shell dirname $(BINARY))
	go build -o $(BINARY)
