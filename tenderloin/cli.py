import sys

from tornado.options import define, options, parse_command_line, print_help

from tenderloin.backend import Carbon
from tenderloin.server import Server

NAGIOS_STATUSES = {
    "OK": 0,
    "WARNING": 1,
    "CRITICAL": 2,
    "UNKNOWN": 3
}


def coerce_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return s


def server():
    define("listen_address", default="127.0.0.1", help="Bind to address")
    define("listen_port", default=50000, help="Web server listen port")

    parse_command_line()
    server = Server(options.listen_address, options.listen_port - 1,
                    options.listen_port)


def collector():
    import logging
    import requests
    import sys
    import time

    define("graphite_address", default="127.0.0.1", group="tc",
           help="Graphite host")
    define("graphite_port", default=2003, group="tc", help="Graphite port")
    define("tenderloin_address", default="127.0.0.1", group="tc",
           help="Tenderloin address")
    define("tenderloin_port", default=50000, group="tc",
           help="Tenderloin port")
    define("interval", default=60, group="tc",
           help="Tenderloin query interval")
    define("noop", default=False, group="tc",
           help="Don't actually send to Graphite")
    define("prefix", default="tl", help="Graphite prefix")

    parse_command_line()

    data = {}
    carbon = Carbon(options.graphite_address, options.graphite_port)

    while True:
        now = int(time.time())
        tl_url = "".join(("http://", options.tenderloin_address, ":",
                          str(options.tenderloin_port)))

        try:
            r = requests.get(tl_url, params=dict(tags="graphite"),
                             timeout=options.interval)
            r.raise_for_status()
        except:
            logging.error("Got bad response code from tenderloin: %s" %
                          sys.exc_info()[1])

        for line in r.content.strip("\n").splitlines():
            (key, val) = line.split(" ", 1)
            key = '.'.join((options.prefix, key))
            data.setdefault(key, [])

            try:
                data[key].append((now, coerce_float(val)))
                if not options.noop:
                    carbon.data = data
                    carbon.send()
            except:
                pass

        sleep_time = options.interval - (int(time.time()) - now)
        if sleep_time > 0:
            logging.info("Sleeping for %d seconds" % sleep_time)
            time.sleep(sleep_time)


def checker():
    import json
    import logging
    import re

    define("tenderloin_address", default="127.0.0.1", group="check_tl",
           help="Tenderloin address")
    define("tenderloin_port", default=50000, group="check_tl",
           help="Tenderloin port")
    define("plugin", group="check_tl", help="Tenderloin plugin to check")
    define("metric", group="check_tl", help="metric to check")
    define("warn", default=None, metavar="VALUE", group="check_tl",
           help="Warning if [not,beyond] VALUE")
    define("crit", default=None, metavar="VALUE", group="check_tl",
           help="Critical if [not,beyond] VALUE")
    define("over", default=False, group="check_tl",
           help="Over specified warning or critical threshold")
    define("under", default=False, group="check_tl",
           help="Under specified warning or critical threshold")
    define("match", multiple=True, group="check_tl",
           help="Critical if metric does not match value specified")

    parse_command_line()

    # hackety-hack to turn off logging
    logging.getLogger().setLevel(logging.FATAL)
    real_warning = coerce_float(options.warn)
    real_critical = coerce_float(options.crit)

    if not any([getattr(options, option) for option in ("warn", "crit", "match")]):
        print "ERROR: You must specify either --warn and --crit or --match values\n"
        print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    if not any([getattr(options, option) for option in ("over", "under", "match")]):
        print "ERROR: You must specify how to interpret the metric with --over or --under or --match\n"
        print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    if not all([getattr(options, option) for option in ("metric", "plugin")]):
        print "ERROR: You must specify both the plugin and metric to check\n"
        print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    if getattr(options, "over") and real_warning > real_critical:
        print "ERROR: warning is over critical!\n"
        print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])
    elif getattr(options, "under") and real_warning < real_critical:
        print "ERROR: warning is under critical!\n"
        print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    tl = Tenderloin(options.tenderloin_address, options.tenderloin_port)
    output = tl.get_data(options.plugin)
    check_output = {}

    try:
        p = re.compile(options.metric)
        for mn, mv in output.items():
            if p.match(mn):
                check_output[mn] = dict(OK=[], WARNING=[], CRITICAL=[])
                mval = coerce_float(output[mn])
                output_string = "%s [warn=%s|crit=%s|recvd=%s]" %\
                                (mn, real_warning, real_critical, mval)

                if options.match:
                    for mx in options.match:
                        p2 = re.compile(mx)
                        if p2.match(mval):
                            check_status = "OK"
                            break
                        else:
                            check_status = "CRITICAL"
                elif options.over:
                    if mval > real_critical:
                        check_status = "CRITICAL"
                    elif real_critical and mval > real_warning:
                        check_status = "WARNING"
                    else:
                        check_status = "OK"
                elif options.under:
                    if mval < real_critical:
                        check_status = "CRITICAL"
                    elif real_warning and mval < real_warning:
                        check_status = "WARNING"
                    else:
                        check_status = "OK"

                check_output[mn][check_status].append(
                    nagios_output(check_status,
                                  mn,
                                  mval,
                                  real_warning,
                                  real_critical))
    except KeyError:
        print "UNKNOWN: Metric doesn't exist: %s" % options.metric
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    if not check_output:
        print "UNKNOWN: Metric doesn't exist: %s" % options.metric
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    critical_statuses = sum([x for x in [v["CRITICAL"] for k, v in check_output.items()] if x], [])
    warning_statuses = sum([x for x in [v["WARNING"] for k, v in check_output.items()] if x], [])
    ok_statuses = sum([x for x in [v["OK"] for k, v in check_output.items()] if x], [])

    if critical_statuses:
        print "\n".join([st for st in critical_statuses])
        sys.exit(NAGIOS_STATUSES["CRITICAL"])
    elif warning_statuses:
        print "\n".join([st for st in warning_statuses])
        sys.exit(NAGIOS_STATUSES["WARNING"])
    else:
        print "\n".join([st for st in ok_statuses])
        sys.exit(NAGIOS_STATUSES["OK"])


def nagios_output(status, metric, value, warning, critical):
    return "%s: %s: [warn=%s|crit=%s|recvd=%s]" %\
        (status.upper(), metric, warning, critical, value)
    sys.exit(NAGIOS_STATUSES[status.upper()])


class Tenderloin(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.url = "http://%s:%s" % (self.host, self.port)

    def get_data(self, plugin_name):
        import requests

        try:
            r = requests.get(self.url, params=dict(tags=plugin_name))
            r.raise_for_status()
        except:
            return None

        return {k: v for k, v in [line.split(" ", 1) for line in r.content.strip("\n").splitlines()]}
