import itertools
import json
import logging
import time
import tornado
import tornado.web

from collections import defaultdict


PLUGIN_DATA = {}


class Listener(object):
    def __init__(self, address="127.0.0.1", port=50000):
        self.address = address
        self.port = port
        self.application = tornado.web.Application([
            (r"/", WebHandler),
            (r"/_send", MessageHandler),
        ])

    def start(self):
        logging.info("Starting up web listener on %s:%d" %
                     (self.address, self.port))
        self.application.listen(self.port, self.address)


class PluginData(object):
    def __init__(self, name, uuid, fqdn, tags, data):
        self.name = name
        self.uuid = uuid
        self.fqdn = fqdn
        self.tags = tags
        self.data = data


class Server(object):
    def __init__(self, listen_address=None, listen_port=50000):
        wl = Listener(listen_address, listen_port)
        wl.start()
        tornado.ioloop.IOLoop.instance().start()


class MessageHandler(tornado.web.RequestHandler):
    def post(self):
        d = json.loads(self.request.body)
        if d["data"]:
            self.update_data(plugin_id=d["plugin_id"], payload=d["data"],
                             tags=d["tags"])

    def update_data(self, plugin_id, payload, tags):
        (plugin_name, uuid, fqdn) = plugin_id
        now = int(time.time())
        payload["received_at"] = now

        logging.debug("Updating plugin: %s@%d" % (repr(plugin_id), now))
        PLUGIN_DATA[plugin_name] = PluginData(name=plugin_name, uuid=uuid,
                                      fqdn=fqdn, tags=tags, data=payload)


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
                                 PLUGIN_DATA.values())

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
