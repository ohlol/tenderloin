import logging
import tornado.web

from tenderloin.listeners import plugin_data


class WebHandler(tornado.web.RequestHandler):
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
            yield " ".join((prefix, ",".join(metrics)))
        else:
            yield " ".join((prefix, str(metrics)))

    def get(self):
        plugin = self.request.uri.split("/", 1)[1]
        response = {}

        if plugin in plugin_data and plugin_data.get(plugin, {}) > 0:
            response = plugin_data[plugin]
        else:
            response = plugin_data

        if len(response) > 0:
            self.set_status(200)
            self.add_header("Content-type", "text/plain")
            for path in self.to_path(plugin_data):
                self.write(path + "\n")
        else:
            self.set_status(404)


class WebListener(object):
    def __init__(self, address = "127.0.0.1", port = 50000):
        self.address = address
        self.port = port
        self.application = tornado.web.Application([
            (r"/.*", WebHandler),
        ])

    def start(self):
        logging.info("Starting up web listener on %s:%d" % (self.address, self.port))
        self.application.listen(self.port, self.address)
