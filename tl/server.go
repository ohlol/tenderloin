package main

import (
	"github.com/jessevdk/go-flags"
	"log"
	"os"
)

func main() {
	var (
		err  error
		opts struct {
			ListenAddr string `short:"l" long:"listen" default:"0.0.0.0:50000" description:"Listen on this address"`
		}
	)

	if _, err = flags.Parse(&opts); err != nil {
		os.Exit(1)
	}

	tenderloinWeb := new(TenderloinWebServer)

	if err = tenderloinWeb.RunServer(opts.ListenAddr); err != nil {
		log.Fatal("could not bind to specified address and/or port")
	}
}
