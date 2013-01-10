NAME = tenderloin
BINARIES = bin/tco bin/tl
SUBDIRS = tco tl
VERSION = 0.3.1
ITERATION = 1
GOPATH=$(PWD)/_go
FPMDOR=$(PWD)/_install
ARCH = $(shell uname -m)
DEPS = `cat DEPS`

.PHONY: all build distclean $(SUBDIRS)

all: build

build: dependencies $(SUBDIRS)

dependencies:
	@for dep in $(DEPS); \
	do \
		go get $$dep; \
	done

deb: all
	mkdir -p $(FPMDIR)/usr/local/bin
	@echo fpm -t deb -s dir -d $(NAME) -v $(VERSION) -a $(ARCH) -C $(FPMDIR) --iteration $(ITERATION) .

distclean:
	rm -rf $(GOPATH) $(BINARIES)

$(SUBDIRS):
	$(MAKE) -C $@
