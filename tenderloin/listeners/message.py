import json
import logging
import time
import zmq

from zmq.eventloop import zmqstream

from tenderloin.listeners import plugin_data

PLUGIN_TIMEOUT = 300


class MessageListener(object):
    def __init__(self, address, port):
        context = zmq.Context()
        socket = context.socket(zmq.PULL)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.HWM, 1000)
        logging.info("Starting up message listener on %s:%d", address, port)
        socket.bind("tcp://%s:%s" % (address, port))
        self.stream = zmqstream.ZMQStream(socket)

    def handle(self, message):
        logging.debug("Received message: %s", repr(message))
        d = json.loads(message[0])

        if d["type"] == "register":
            self.register_plugin(plugin_id=d["id"])
        elif d["type"] == "data" and len(d["data"]) > 0:
            self.update_data(plugin_id=d["id"], payload=d["data"])

    def update_data(self, plugin_id, payload):
        payload["received_at"] = int(time.time())
        (plugin_name, fqdn) = plugin_id.split("%", 1)

        if plugin_name in plugin_data and fqdn in plugin_data[plugin_name]:
            plugin_data[plugin_name][fqdn] = payload

    def consumer_loop(self):
        self.stream.on_recv(self.handle)

    def register_plugin(self, plugin_id):
        global PLUGIN_TIMEOUT

        now = time.time()
        (plugin_name, fqdn) = plugin_id.split("%", 1)
        if plugin_name in plugin_data and fqdn in plugin_data[plugin_name]:
            plugin_expiry_time = now - PLUGIN_TIMEOUT
            if "received_at" in plugin_data[plugin_name][fqdn] and plugin_data[plugin_name][fqdn]["received_at"] < plugin_expiry_time:
                logging.info("Re-registering plugin due to expiry: %s@%d" % (repr(plugin_id), now))
        else:
            logging.info("Registering plugin: %s@%d" % (repr(plugin_id), now))
            plugin_data[plugin_name][fqdn] = {}
