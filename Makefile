BINARIES = bin/tco bin/tl
SUBDIRS = tco tl

.PHONY: all build distclean $(SUBDIRS)

all: build

build: $(SUBDIRS)

distclean:
	rm -rf _go $(BINARIES)

$(SUBDIRS):
	$(MAKE) -C $@
