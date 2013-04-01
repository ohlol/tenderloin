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
		if v != nil {
			realPrefix = prefixed(prefix, k)
			switch reflect.TypeOf(v).Kind() {
			case reflect.Map:
				mm := MetricsMap(v.(map[string]interface{}))
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
			case reflect.Float64:
				metrics = append(metrics, fmt.Sprintf("%s %f", realPrefix, v))
			}
		}
	}

	return metrics
}
