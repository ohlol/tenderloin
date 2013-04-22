NAME = tenderloin
BINARIES = bin/tco bin/tl
SUBDIRS = tco tl
VERSION = 0.3.2
ITERATION = 1
GOPATH = $(PWD)/_go
FPMDIR = $(PWD)/_install
ARCH = $(shell uname -m)
DEPS = `cat DEPS`

.PHONY: all build dependencies deb distclean staticfiles $(SUBDIRS)

all: build

build: dependencies $(SUBDIRS)

deb: all staticfiles
	mkdir -p $(FPMDIR)/usr/bin
	cp $(BINARIES) $(FPMDIR)/usr/bin
	fpm -t deb -s dir -n $(NAME) -v $(VERSION) -a $(ARCH) -C $(FPMDIR) --iteration $(ITERATION) .

dependencies:
	@for dep in $(DEPS); \
	do \
		go get $$dep; \
	done

distclean:
	rm -rf $(GOPATH) $(BINARIES) $(FPMDIR)

$(SUBDIRS):
	$(MAKE) -C $@

staticfiles:
	mkdir -p $(FPMDIR)/usr/share/tenderloin
	cp -r graphs static $(FPMDIR)/usr/share/tenderloin
