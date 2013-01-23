$(function() {
    var allMetrics = {}
      , chartSelectors = []

    function Plugin(name) {
        this.name = name
        this.metrics = ko.observableArray()
    }

    function MetricsViewModel() {
        var self = this
          , metrics = {}
          , plugins = []

        self.plugins = ko.observableArray()

        $.get("/?tags=graphite", function(data) {
            $.map(data.split("\n"), function(line) {
                if (line.length > 0) {
                    var mLine = line.split(" ", 2)
                    var pluginMetric = mLine[0].split(".")
                    var plugin = pluginMetric.shift()
                    var metric = pluginMetric.join(".")
                    var selector = ["chart", plugin, metric].join("-")

                    if (!metrics.hasOwnProperty(plugin)) {
                        metrics[plugin] = []
                    }

                    if (metric.indexOf("received_at", metric.length - "received_at".length) === -1) {
                        var val = parseFloat(mLine[1])
                        if (val !== NaN) {
                            metrics[plugin].push([
                                metric,
                                selector,
                                Array(20).join("0,") + val
                            ])
                        }
                    }
                }
            })

            for (var key in metrics) {
                var plugin = new Plugin(key)
                plugin.metrics = metrics[key]
                plugins.push(plugin)
            }

            self.plugins(plugins)
        })
    }

    setInterval(function() {
        var metrics = {}

        $.get("/?tags=graphite", function(data) {
            var metrics = {}

            $.map(data.split("\n"), function(line) {
                if (line.length > 0) {
                    var mLine = line.split(" ", 2)
                    var pluginMetric = mLine[0].split(".")
                    var plugin = pluginMetric.shift()
                    var metric = pluginMetric.join(".")

                    if (!metrics.hasOwnProperty(plugin)) {
                        metrics[plugin] = {}
                    }

                    if (metric !== "received_at") {
                        var val = parseFloat(mLine[1])
                        if (val !== NaN) {
                            metrics[plugin][metric] = val
                        }
                    }
                }
            })

            for (var i = 0; i < chartSelectors.length; i++) {
                var id = $(chartSelectors[i]).attr("id").split("-")
                  , values = $(chartSelectors[i]).text().split(",")

                if (metrics.hasOwnProperty(id[1])) {
                    if (metrics[id[1]].hasOwnProperty(id[2])) {
                        values.shift()

                        var val = parseFloat(metrics[id[1]][id[2]])
                        values.push(metrics[id[1]][id[2]])
                        $(chartSelectors[i])
                            .text(values.join(","))
                            .change()
                    }
                }
            }
        })

    }, 1000)

    ko.applyBindings(new MetricsViewModel())

    ko.bindingHandlers.renderChart = {
        init: function(element) {
            $(element).peity("line", { width: 250, height: 20 })
            chartSelectors.push(element)
        }/*,
        update: function(element) {
            $(element).peity("bar", { width: 250, height: 20 })
        }*/
    }
})
