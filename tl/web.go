package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sort"
	"strings"
	"time"
)

type Plugin struct {
	data MetricsMap
	name string
	tags Set
}

type Set []string

type TenderloinWebServer struct{}

type MetricsData struct {
	data map[string]Plugin
}

func Log(handler http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s %s", r.RemoteAddr, r.Method, r.URL)
		handler.ServeHTTP(w, r)
	})
}

func filterByTags(tags Set, metrics MetricsData) []Plugin {
	plugins := []Plugin{}

	for _, m := range metrics.data {
		if t := tags.Subset(m.tags); len(t) > 0 {
			plugins = append(plugins, m)
		}
	}

	return plugins
}

func formatFqdn() string {
	fqdn, _ := os.Hostname()
	splitName := strings.Split(fqdn, ".")

	for i, j := 0, len(splitName)-1; i < j; i, j = i+1, j-1 {
		splitName[i], splitName[j] = splitName[j], splitName[i]
	}

	return strings.Join(splitName, ".")
}

func messageHandler(w http.ResponseWriter, r *http.Request, updater chan Plugin) {
	var (
		data MetricsMap
		err  error
		tags Set
	)

	pluginName := r.FormValue("plugin_id")

	json.Unmarshal([]byte(r.FormValue("tags")), &tags)

	if err = json.Unmarshal([]byte(r.FormValue("data")), &data); err != nil {
		log.Printf("failed to unmarshal plugin data for %s: %s", pluginName, err)
	} else {
		data["received_at"] = fmt.Sprintf("%d", time.Now().Unix())
		updater <- Plugin{name: pluginName, data: data, tags: tags}
	}
}

func prefixed(prefix string, val string) string {
	realPrefix := ""

	if len(prefix) > 0 {
		realPrefix = fmt.Sprintf("%s.%s", prefix, val)
	} else {
		realPrefix = val
	}

	return realPrefix
}

func webHandler(w http.ResponseWriter, r *http.Request, metrics *MetricsData) {
	tags := []string{}
	fqdn := formatFqdn()
	tagsParam := r.FormValue("tags")
	paths := []string{}

	if len(tagsParam) > 0 {
		tags = strings.Split(tagsParam, ",")
	}

	if len(tags) > 0 {
		if filtered := filterByTags(tags, *metrics); len(filtered) > 0 {
			for _, plugin := range filtered {
				for _, pth := range plugin.data.ToPath(fqdn) {
					paths = append(paths, pth)
				}
			}
		}
	} else {
		for _, plugin := range metrics.data {
			for _, pth := range plugin.data.ToPath(fqdn) {
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
	)

	metrics.data = make(map[string]Plugin)
	updates := make(chan Plugin)
	go updateFunc(updates, &metrics)

	// The handler wrappers are so simple it seems just as simple to use closures.
	webHandlerFunc := func(w http.ResponseWriter, r *http.Request) {
		webHandler(w, r, &metrics)
	}
	messageHandlerFunc := func(w http.ResponseWriter, r *http.Request) {
		messageHandler(w, r, updates)
	}

	http.HandleFunc("/", webHandlerFunc)
	http.HandleFunc("/_send", messageHandlerFunc)
	log.Printf("starting server up on %s", listenAddr)

	return http.ListenAndServe(listenAddr, Log(http.DefaultServeMux))
}

func updateFunc(updates chan Plugin, metrics *MetricsData) {
	for plugin := range updates {
		metrics.data[plugin.name] = plugin
	}
}
