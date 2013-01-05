package main

import (
	"github.com/jessevdk/go-flags"
	"log"
	"os"
)

var opts struct {
	ListenAddr string `short:"l" long:"listen" default:"0.0.0.0:50000" description:"Listen on this address"`
}

func main() {
	var (
		err error
	)

	_, err = flags.Parse(&opts)
	if err != nil {
		os.Exit(1)
	}

	tenderloinWeb := new(TenderloinWebServer)
	err = tenderloinWeb.RunServer(opts.ListenAddr)

	if err != nil {
		log.Fatal("Could not bind to specified address and/or port")
	}
}
