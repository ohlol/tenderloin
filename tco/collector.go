package main

import (
	"errors"
	"fmt"
	"github.com/jessevdk/go-flags"
	"github.com/ohlol/graphite-go"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
)

func fetchData(url string) (error, []byte) {
	var (
		data []byte
		err  error
		res  *http.Response
	)

	if res, err = http.Get(url); err != nil {
		return errors.New(fmt.Sprintf("problem querying tenderloin: %s", err)), data
	}
	if res.StatusCode != 200 {
		return errors.New("problem querying tenderloin: no plugins matched"), data
	}

	if data, err = ioutil.ReadAll(res.Body); err != nil {
		return errors.New(fmt.Sprintf("problem querying tenderloin: %s", err)), data
	}

	return nil, data
}

func parseTenderloinOutput(prefix, data string) []graphite.Metric {
	var (
		key        string
		metrics    []graphite.Metric
		metricLine []string
		val        string
	)

	now := time.Now().Unix()

	for _, line := range strings.Split(data, "\n") {
		if line != "" {
			metricLine = strings.SplitN(line, " ", 2)
			key = strings.Join([]string{prefix, metricLine[0]}, ".")
			val = metricLine[1]
			metrics = append(metrics, graphite.Metric{Name: key, Value: val, Timestamp: now})
		}
	}

	return metrics
}

func main() {
	var (
		data []byte
		err  error
		opts struct {
			TenderloinAddr string `long:"tenderloin-address" default:"127.0.0.1:50000" description:"Tenderloin address"`
			GraphiteAddr   string `long:"graphite-address" default:"127.0.0.1" description:"Graphite address"`
			GraphitePort   uint16 `long:"graphite-port" default:"2003" description:"Graphite port"`
			Interval       int    `short:"i" long:"interval" default:"60" description:"Tenderloin query interval"`
			Noop           bool   `short:"n" long:"noop" default:"false" description:"Don't actually send to Graphite"`
			Prefix         string `short:"p" long:"prefix" default:"tl" description:"Graphite prefix"`
		}
	)

	if _, err = flags.Parse(&opts); err != nil {
		os.Exit(1)
	}

	tenderloinUrl := fmt.Sprintf("http://%s/?tags=graphite", opts.TenderloinAddr)
	graphite := graphite.Connect(graphite.GraphiteServer{Host: opts.GraphiteAddr, Port: opts.GraphitePort})

	for {
		if err, data = fetchData(tenderloinUrl); err != nil {
			log.Println(err)
		} else {
			graphite.Sendall(parseTenderloinOutput(opts.Prefix, string(data)))
		}

		time.Sleep(time.Duration(opts.Interval) * time.Second)
	}
}
