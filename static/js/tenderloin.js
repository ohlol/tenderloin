$(function() {
    updater.start()

    // have to do this here due to the tabs
    d3.select(".tab-content").call(function(div){
        div.insert("div")
            .attr("class", "rule")
            .call(context.rule())
    })
})

var contexts = {}

/*
 * Each metric is a regex to match output from tenderloin.
 * Tabs are created based on the second field (dot-delimited).
 * So in the default metrics, you get four tabs.
 */
var metrics = [
        "base.cpu.cpu(?!.*(idle|softirq))",
        "base.diskstats.*",
        "base.loadavg.*term",
        "base.meminfo.(mem|swap)(free|used)"
    ]

function getOrElseUpdate(map, k, callback) {
    var v = map[k]
    if (v !== undefined) return v
    return map[k] = callback()
}

var updater = {
    socket: null,
    start: function() {
        var url = "ws://" + location.host + "/_poller"

        if ("WebSocket" in window) {
            updater.socket = new WebSocket(url)
        } else {
            updater.socket = new MozWebSocket(url)
        }

        var registering = setInterval(function(){
            updater.socket.send(JSON.stringify({
                command:"filter",
                tags:["graphite"],
                interval:1
            }))
        }, 1000)

        updater.socket.onmessage = function(event) {
            parsed = JSON.parse(event.data)
            if (parsed.hasOwnProperty("Data")) {
                switch(parsed["Data"]) {
                case "registered":
                    clearInterval(registering)
                    break
                default:
                    var metric = parsed["Data"]
                        , name = metric[0]
                        , value = metric[1]
                        , timestamp = metric[2]

                    for(var i = 0; i < metrics.length; i++) {
                        if (name.match(metrics[i])) {
                            var tab = name.split(".", 2)[1]
                                , selector = "#"+tab+" .tab-data"
                                , axis = d3.select("#"+tab+" .axis")
                                , ctx = getOrElseUpdate(contexts, name, function(){
                                    var x = tenderloinContext(name)
                                    setup_context(selector, x.data_context)
                                    return x
                                })

                            if (axis.empty()) {
                                d3.select(selector).call(function(div){
                                    div.insert("div", ":first-child")
                                        .attr("class", "axis")
                                        .call(context.axis().orient("top"))
                                })
                            }

                            ctx.update(timestamp, +value)
                        }
                    }

                    break
                }
            }
        }
    }
}

var context = cubism.context()
    .serverDelay(0)
    .clientDelay(0)
    .step(1e3)
    .size(940)

context.on("focus", function(i) {
  d3.selectAll(".value").style("right", i == null ? null : context.size() - i + "px")
})

function tenderloinContext(name) {
    var values = {}
        , max = 0
        , counter = 0
        , dc = context.metric(function(start, stop, step, callback) {
            var rv = []

            start = +start, stop = +stop

            while (start < stop) {
                start += step
                var possible_v = values[start]
                if (possible_v !== undefined)
                    rv.push(possible_v)
            }

            callback(null, rv)
        }, name + "")

    return {
        data_context: dc,
        update: function(timestamp, value) {
            values[timestamp] = value
            counter += 1
            if (counter > 940) delete values[timestamp - 940 * 1000]
        }
    }
}

function setup_context(selector, data_context) {
    d3.select(selector).call(function(div) {
        div.datum(data_context)
        div.append("div")
            .attr("class", "horizon")
            .call(context.horizon()
                  .height(30)
                  .colors(["#FFFFCC", "#FFEDA0", "#FED976", "#FEB24C", "#FD8D3C", "#FC4E2A", "#E31A1C", "#BD0026", "#800026"]))
    })

    $(".tab-data .horizon").tsort()
}
