#!/usr/bin/env python

import json
import optparse
import re
import sys
import urllib2

from urllib import urlencode

NAGIOS_STATUSES = {
    "OK": 0,
    "WARNING": 1,
    "CRITICAL": 2,
    "UNKNOWN": 3
}


class Tenderloin(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.url = "http://%s:%s" % (self.host, self.port)

    def get_data(self, plugin_name):
        try:
            qargs = urlencode(dict(tags=plugin_name))
            response = urllib2.urlopen("?".join((self.url, qargs)))

            if response.code == 200:
                return {k: v for k, v in [line.split(" ", 1) for line in response.read().splitlines()]}
            else:
                return None
        except urllib2.URLError, TypeError:
            return None

def coerce_number(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return s

def nagios_output(status, metric, value, warning, critical):
    print "%s: %s: [warn=%s|crit=%s|recvd=%s]" %\
        (status.upper(), metric, warning, critical, mval)
    sys.exit(NAGIOS_STATUSES[status.upper()])

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-H", dest="host",
                      default="localhost",
                      help="Tenderloin host [%default]")
    parser.add_option("-p", dest="port",
                      default=50000,
                      type="int",
                      help="Tenderloin port [%default]")
    parser.add_option("-P", "--plugin", dest="plugin",
                      help="Tenderloin plugin to check")
    parser.add_option("-m", "--metric", dest="metric",
                      help="metric to check")
    parser.add_option("-W", dest="warning",
                      default=None,
                      metavar="VALUE",
                      help="Warning if [not,beyond] VALUE")
    parser.add_option("-C", dest="critical",
                      default=None,
                      metavar="VALUE",
                      help="Critical if [not,beyond] VALUE")
    parser.add_option("--over", dest="over",
                      default=False,
                      action="store_true",
                      help="Over specified warning or critical threshold")
    parser.add_option("--under", dest="under",
                      default=False,
                      action="store_true",
                      help="Under specified warning or critical threshold")
    parser.add_option("--match", dest="match",
                      action="append",
                      help="Critical if metric does not match value specified")

    (options, args) = parser.parse_args()

    real_warning = coerce_number(options.warning)
    real_critical = coerce_number(options.critical)

    if not any([getattr(options, option) for option in ("warning", "critical", "match")]):
        print "ERROR: You must specify either -W and -C or --match values\n"
        parser.print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    if not any([getattr(options, option) for option in ("over", "under", "match")]):
        print "ERROR: You must specify how to interpret the metric with --over or --under\n"
        parser.print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    if not all([getattr(options, option) for option in ("metric", "plugin")]):
        print "ERROR: You must specify both the plugin and metric to check\n"
        parser.print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    if getattr(options, "over") and real_warning > real_critical:
        print "ERROR: warning is over critical!\n"
        parser.print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])
    elif getattr(options, "under") and real_warning < real_critical:
        print "ERROR: warning is under critical!\n"
        parser.print_help()
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    tl = Tenderloin(options.host, options.port)
    output = tl.get_data(options.plugin)
    check_output = {}

    try:
        p = re.compile(options.metric)
        for mn, mv in output.iteritems():
            if p.match(mn):
                check_output[mn] = dict(OK=[], WARNING=[], CRITICAL=[])
                mval = coerce_number(output[mn])

                if options.match:
                    for mx in options.match:
                        p2 = re.compile(mx)
                        if p2.match(mval):
                            check_status = "OK"
                            break
                        else:
                            check_status = "CRITICAL"
                    check_output[mn][check_status].append("%s [warn=%s|crit=%s|recvd=%s]" % (mn, options.warning, options.critical, mval))
                elif options.over:
                    if mval > real_critical:
                        check_output[mn]["CRITICAL"].append("%s [warn=%s|crit=%s|recvd=%s]" % (mn, options.warning, options.critical, mval))
                    elif options.warning and mval > real_warning:
                        check_output[mn]["WARNING"].append("%s [warn=%s|crit=%s|recvd=%s]" % (mn, options.warning, options.critical, mval))
                    else:
                        check_output[mn]["OK"].append("%s [warn=%s|crit=%s|recvd=%s]" % (mn, options.warning, options.critical, mval))
                elif options.under:
                    if mval < real_critical:
                        check_output[mn]["CRITICAL"].append("%s [warn=%s|crit=%s|recvd=%s]" % (mn, options.warning, options.critical, mval))
                    elif options.warning and mval < real_warning:
                        check_output[mn]["WARNING"].append("%s [warn=%s|crit=%s|recvd=%s]" % (mn, options.warning, options.critical, mval))
                    else:
                        check_output[mn]["OK"].append("%s [warn=%s|crit=%s|recvd=%s]" % (mn, options.warning, options.critical, mval))
    except KeyError:
        print "UNKNOWN: Metric doesn't exist: %s" % options.metric
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    if not check_output:
        print "UNKNOWN: Metric doesn't exist: %s" % options.metric
        sys.exit(NAGIOS_STATUSES["UNKNOWN"])

    critical_statuses = sum([x for x in [v["CRITICAL"] for k,v in check_output.iteritems()] if x], [])
    warning_statuses = sum([x for x in [v["WARNING"] for k,v in check_output.iteritems()] if x], [])
    ok_statuses = sum([x for x in [v["OK"] for k,v in check_output.iteritems()] if x], [])

    if critical_statuses:
        print "\n".join(["CRITICAL: %s" % st for st in critical_statuses])
        sys.exit(NAGIOS_STATUSES["CRITICAL"])
    elif warning_statuses:
        print "\n".join(["WARNING: %s" % st for st in warning_statuses])
        sys.exit(NAGIOS_STATUSES["WARNING"])
    else:
        print "\n".join(["OK: %s" % st for st in ok_statuses])
        sys.exit(NAGIOS_STATUSES["OK"])
