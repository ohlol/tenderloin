package main

import (
	"fmt"
	"reflect"
	"strings"
)

type MetricsMap map[string]interface{}

type Metrics interface {
	ToPath()
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

func (mMap *MetricsMap) ToPath(prefix string) []string {
	var (
		realPrefix string
	)

	metrics := []string{}

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
			for _, d := range v.([]interface{}) {
				slc = append(slc, fmt.Sprintf("%s", d))
			}
			metrics = append(metrics, fmt.Sprintf("%s %s", realPrefix, strings.Join(slc, ",")))
		case reflect.String:
			metrics = append(metrics, fmt.Sprintf("%s %s", realPrefix, v))
		}
	}

	return metrics
}
