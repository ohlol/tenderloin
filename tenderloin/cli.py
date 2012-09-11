from tornado.options import define, options, parse_command_line

from tenderloin.backend import Carbon
from tenderloin.server import Server


def coerce_number(s):
    try:
        return int(s)
    except:
        return float(s)

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

    define("graphite_address", default="127.0.0.1", help="Graphite host")
    define("graphite_port", default=2003, help="Graphite port")
    define("tenderloin_address", default="127.0.0.1", help="Tenderloin address")
    define("tenderloin_port", default=50000, help="Tenderloin port")
    define("interval", default=60, help="Tenderloin query interval")
    define("noop", default=False, help="Noop send to Graphite")
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
                data[key].append((now, coerce_number(val)))
                if not options.noop:
                    carbon.data = data
                    carbon.send()
            except:
                pass

        sleep_time = options.interval - (int(time.time()) - now)
        if sleep_time > 0:
            logging.info("Sleeping for %d seconds" % sleep_time)
            time.sleep(sleep_time)
