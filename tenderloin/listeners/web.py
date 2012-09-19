import itertools
import logging
import tornado.web

from collections import defaultdict

from tenderloin.listeners import plugin_data


class WebHandler(tornado.web.RequestHandler):
    def format_fqdn(self, fqdn):
        return ".".join(reversed(fqdn.split(".")))

    def to_path(self, metrics, prefix=""):
        if isinstance(metrics, dict):
            for k, v in metrics.items():
                if prefix:
                    real_prefix = ".".join((prefix, k))
                else:
                    real_prefix = k

                for line in self.to_path(v, real_prefix):
                    yield line
        elif isinstance(metrics, list):
            yield " ".join((prefix, ",".join([repr(m) for m in metrics])))
        else:
            yield " ".join((prefix, str(metrics)))

    def filter_by_tags(self, tags):
        return itertools.ifilter(lambda x: set(tags) < set(x.tags),
                                 plugin_data)

    def get(self):
        tags = [t for t in self.get_argument("tags", default="").split(",") if t]
        response = defaultdict(dict)

        for plugin in self.filter_by_tags(tags):
            response[self.format_fqdn(plugin.fqdn)].update({
                plugin.name: plugin.data
            })

        if response:
            self.set_status(200)
            self.add_header("Content-type", "text/plain")
            for path in sorted(self.to_path(response)):
                self.write(path + "\n")
        else:
            self.set_status(404)


class WebListener(object):
    def __init__(self, address="127.0.0.1", port=50000):
        self.address = address
        self.port = port
        self.application = tornado.web.Application([
            (r"/.*", WebHandler),
        ])

    def start(self):
        logging.info("Starting up web listener on %s:%d" %
                     (self.address, self.port))
        self.application.listen(self.port, self.address)
