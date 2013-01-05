package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"reflect"
	"sort"
	"strings"
	"time"
)

type MetricsMap map[string]interface {}

type Metrics interface {
	ToPath()
}

type Plugin struct {
	name string
	data MetricsMap
	tags Set
}

type Set []string

type TenderloinWebServer struct {}

var MetricsData = map[string] Plugin{}

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
		err error
		tags Set
	)

	pluginName := r.FormValue("plugin_id")

	json.Unmarshal([]byte(r.FormValue("tags")), &tags)
	err = json.Unmarshal([]byte(r.FormValue("data")), &data)
	data["received_at"] = fmt.Sprintf("%d", time.Now().Unix())

	if err == nil {
		MetricsData[pluginName] = Plugin{name:pluginName, data:data, tags:tags}
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
	//paths := MetricsData.ToPath(fqdn)

	if len(paths) > 0 {
		sort.Strings(paths)
		for _, metric := range paths {
			fmt.Fprintf(w, "%s\n", metric)
		}
	} else {
		http.Error(w, "No plugins matched.", 404)
	}
}

func (mMap *MetricsMap) ToPath(prefix string) []string {
	metrics := []string{}
	var realPrefix string

	for k, v := range *mMap {
		realPrefix = prefixed(prefix, k)
		switch reflect.TypeOf(v).Kind() {
		case reflect.Map:
			mm := MetricsMap(v.(MetricsMap))
			for _, pth := range mm.ToPath(realPrefix) {
				metrics = append(metrics, pth)
			}
		case reflect.Slice:
			slc := []string{}
			for _, d := range v.([]interface {}) {
				slc = append(slc, fmt.Sprintf("%s", d))
			}
			metrics = append(metrics, fmt.Sprintf("%s %s", realPrefix, strings.Join(slc, ",")))
		case reflect.String:
			metrics = append(metrics, fmt.Sprintf("%s %s", realPrefix, v))
		}
	}
	return metrics
}

func (s1 *Set) Subset(s2 Set) []string {
	var subset Set

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
