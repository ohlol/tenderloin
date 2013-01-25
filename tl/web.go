package main

import (
	"code.google.com/p/go.net/websocket"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"sort"
	"strings"
	"time"
)

type MetricsData struct {
	Plugins map[string]Plugin
}

type Plugin struct {
	Data     MetricsMap
	Interval int
	Name     string
	Tags     Set
}

type Set []string

type TenderloinWebServer struct{}

func Log(handler http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s %s", r.RemoteAddr, r.Method, r.URL)
		handler.ServeHTTP(w, r)
	})
}

func filterByTags(tags Set, metrics MetricsData) []Plugin {
	plugins := []Plugin{}

	for _, plugin := range metrics.Plugins {
		if t := tags.Subset(plugin.Tags); len(t) > 0 {
			plugins = append(plugins, plugin)
		}
	}

	return plugins
}

func messageHandler(w http.ResponseWriter, r *http.Request, updater chan Plugin) {
	var (
		body   []byte
		plugin Plugin
		err    error
	)

	if body, err = ioutil.ReadAll(r.Body); err != nil {
		log.Printf("couldn't read request body")
	} else {
		if err = json.Unmarshal(body, &plugin); err != nil {
			log.Printf("failed to unmarshal plugin data: %s", err)
		} else {
			if len(plugin.Name) == 0 {
				log.Printf("no plugin name specified")
				return
			}

			if plugin.Interval <= 0 {
				plugin.Interval = 60
			}

			plugin.Tags = append(plugin.Tags, plugin.Name)
			plugin.Data["received_at"] = fmt.Sprintf("%d", time.Now().Unix())
			updater <- plugin
		}
	}
}

func pollerHandler(ws *websocket.Conn, pool *ConnectionPool, metrics MetricsData) {
	c := &Connection{send: make(chan string), ws: ws, interval: 1}
	pool.register <- c
	defer func() { pool.unregister <- c }()
	go c.writer(metrics)
	c.reader()
}

func updateMetrics(updates chan Plugin, metrics *MetricsData) {
	for plugin := range updates {
		metrics.Plugins[plugin.Name] = plugin
	}
}

func webHandler(w http.ResponseWriter, r *http.Request, metrics MetricsData) {
	tags := []string{}
	tagsParam := r.FormValue("tags")
	paths := []string{}

	if len(tagsParam) > 0 {
		tags = strings.Split(tagsParam, ",")
	}

	if len(tags) > 0 {
		if filtered := filterByTags(tags, metrics); len(filtered) > 0 {
			for _, plugin := range filtered {
				for _, pth := range plugin.Data.ToPath(plugin.Name) {
					paths = append(paths, pth)
				}
			}
		}
	} else {
		for _, plugin := range metrics.Plugins {
			for _, pth := range plugin.Data.ToPath(plugin.Name) {
				paths = append(paths, pth)
			}
		}
	}

	if len(paths) > 0 {
		sort.Strings(paths)
		for _, metric := range paths {
			fmt.Fprintf(w, "%s\n", metric)
		}
	} else {
		http.Error(w, "no plugins matched.", 404)
	}
}

func (s1 *Set) Subset(s2 Set) []string {
	var (
		subset Set
	)

	for _, k := range *s1 {
		for _, j := range s2 {
			if k == j {
				subset = append(subset, k)
			}
		}
	}

	return subset
}

func (tenderloinServer *TenderloinWebServer) RunServer(listenAddr string) error {
	var (
		metrics MetricsData
		pool ConnectionPool
	)

	metrics.Plugins = make(map[string]Plugin)
	updates := make(chan Plugin)
	go updateMetrics(updates, &metrics)

	pool.register = make(chan *Connection)
	pool.unregister = make(chan *Connection)
	pool.connections = make(map[*Connection]bool)
	go pool.run()

	// The handler wrappers are so simple it seems just as simple to use closures.
	graphHandlerFunc := func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "graphs/index.html")
	}
	messageHandlerFunc := func(w http.ResponseWriter, r *http.Request) {
		messageHandler(w, r, updates)
	}
	pollerHandlerFunc := func(ws *websocket.Conn) {
		pollerHandler(ws, &pool, metrics)
	}
	webHandlerFunc := func(w http.ResponseWriter, r *http.Request) {
		webHandler(w, r, metrics)
	}

	http.HandleFunc("/", webHandlerFunc)
	http.HandleFunc("/_send", messageHandlerFunc)
	http.Handle("/_poller", websocket.Handler(pollerHandlerFunc))
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("static"))))
	http.HandleFunc("/graphs", graphHandlerFunc)
	log.Printf("starting server up on %s", listenAddr)

	return http.ListenAndServe(listenAddr, Log(http.DefaultServeMux))
}
