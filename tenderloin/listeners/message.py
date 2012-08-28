from zmq.eventloop import zmqstream

import json
import logging
import time
import zmq

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
            self.register_plugin(name=d["plugin"], id=d["id"])
        elif d["type"] == "data":
            self.update_data(plugin=d["plugin"], payload=d["data"])

    def update_data(self, plugin, payload):
        payload["received_at"] = int(time.time())
        plugin_data[plugin] = payload

    def consumer_loop(self):
        self.stream.on_recv(self.handle)

    def register_plugin(self, name, id):
        global PLUGIN_TIMEOUT

        if name in plugin_data:
            now = time.time()
            plugin_expiry_time = now - PLUGIN_TIMEOUT
            if "received_at" in plugin_data[name] and plugin_data[name]["received_at"] < plugin_expiry_time:
                logging.debug("Re-registering plugin due to expiry: %s@%d" % (name, now))
            else:
                logging.debug("Registering plugin: %s@%d" % (name, now))
