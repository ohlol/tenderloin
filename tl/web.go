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

var (
	MetricsData = map[string]Plugin{}
)

func Log(handler http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s %s", r.RemoteAddr, r.Method, r.URL)
		handler.ServeHTTP(w, r)
	})
}

func filterByTags(tags Set) []Plugin {
	plugins := []Plugin{}

	for _, m := range MetricsData {
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

func messageHandler(w http.ResponseWriter, r *http.Request) {
	var (
		data MetricsMap
		err  error
		tags Set
	)

	pluginName := r.FormValue("plugin_id")

	json.Unmarshal([]byte(r.FormValue("tags")), &tags)

	err = json.Unmarshal([]byte(r.FormValue("data")), &data)
	if err == nil {
		data["received_at"] = fmt.Sprintf("%d", time.Now().Unix())
		MetricsData[pluginName] = Plugin{name: pluginName, data: data, tags: tags}
	} else {
		log.Printf("Failed to unmarshal plugin data for %s!", pluginName)
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

func webHandler(w http.ResponseWriter, r *http.Request) {
	tags := []string{}
	fqdn := formatFqdn()
	tagsParam := r.FormValue("tags")
	paths := []string{}

	if len(tagsParam) > 0 {
		tags = strings.Split(tagsParam, ",")
	}

	if len(tags) > 0 {
		if filtered := filterByTags(tags); len(filtered) > 0 {
			for _, plugin := range filtered {
				for _, pth := range plugin.data.ToPath(fqdn) {
					paths = append(paths, pth)
				}
			}
		}
	} else {
		for _, plugin := range MetricsData {
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
		http.Error(w, "No plugins matched.", 404)
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
	http.HandleFunc("/", webHandler)
	http.HandleFunc("/_send", messageHandler)
	log.Printf("Starting server up on %s", listenAddr)

	return http.ListenAndServe(listenAddr, Log(http.DefaultServeMux))
}
