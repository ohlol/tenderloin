import logging
import tornado.web

from collections import defaultdict

from tenderloin.listeners import plugin_data


class WebHandler(tornado.web.RequestHandler):
    def format_fqdn(self, fqdn):
        return ".".join(reversed(fqdn.split(".")))

    def to_path(self, metrics, prefix=""):
        if isinstance(metrics, dict):
            for k, v in metrics.iteritems():
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

    def get(self):
        plugin = self.request.path.lstrip("/")
        fqdn = self.get_argument("fqdn", default=None)
        response = defaultdict(dict)

        if plugin:
            if fqdn:
                if plugin_data.get(plugin, {})\
                              .get(fqdn, {}):
                    response = {self.format_fqdn(fqdn): {plugin: plugin_data[plugin][fqdn]}}
            else:
                response = {self.format_fqdn(f): {plugin: plugin_data[plugin][f]} for f in plugin_data[plugin]}
        else:
            # {plugin: {fqdn: data}} -> {fqdn: {plugin: data}}
            # ... with fqdn reversed on periods.
            for plugin in plugin_data:
                if fqdn:
                    if fqdn in plugin_data[plugin]:
                        response[self.format_fqdn(fqdn)][plugin] = plugin_data[plugin][fqdn]
                else:
                    for fqdn in plugin_data[plugin]:
                        response[self.format_fqdn(fqdn)][plugin] = plugin_data[plugin][fqdn]

        if response:
            self.set_status(200)
            self.add_header("Content-type", "text/plain")
            for path in self.to_path(response):
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
