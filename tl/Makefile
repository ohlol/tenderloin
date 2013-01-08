BINARY = ../bin/tl
GOFILES = \
	metrics.go \
	server.go \
	web.go

.PHONY: all $(BINARY)

all: tl

tl: $(GOFILES) $(BINARY)
	go build -o $(BINARY)
