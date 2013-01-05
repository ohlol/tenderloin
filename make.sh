#!/bin/sh

export GOPATH=`pwd`/_go

for dep in $(cat DEPS)
do
    go get $dep
done

make
