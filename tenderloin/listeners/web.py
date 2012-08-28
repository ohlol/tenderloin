import logging
import tornado.web

from tenderloin.listeners import plugin_data

def logger():
    return tornado.web.Application.log


class WebHandler(tornado.web.RequestHandler):
    def to_path(self, metrics):
        formatted = []

        def helper(data, path, formatted):
            for key, val in data.iteritems():
                if isinstance(val,  dict):
                    helper(val, "".join((path, key)), formatted)
                else:
                    formatted.append("%s %s" % (".".join((path, key.replace(".","_"))), val))

        helper(metrics, "", formatted)
        return formatted

    def get(self):
        if len(plugin_data):
            self.set_status(200)
            self.add_header("Content-type", "text/plain")
            self.write("\n".join(self.to_path(plugin_data)) + "\n")


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
