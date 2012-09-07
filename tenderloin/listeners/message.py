import json
import logging
import time
import zmq

from collections import defaultdict
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
        d = json.loads(message[0])

        if d["data"]:
            self.update_data(plugin_id=d["plugin_id"], payload=d["data"])

    def update_data(self, plugin_id, payload):
        (plugin_name, uuid, fqdn) = plugin_id
        now = int(time.time())
        payload["received_at"] = now

        self.register_plugin(plugin_id)

        if self.registered(plugin_id) == uuid:
            logging.debug("Updating plugin: %s@%d" % (repr(plugin_id), now))
            plugin_data[plugin_name][fqdn]["data"] = payload
        else:
            logging.info("Ignoring plugin data due to registration collision: %s" % repr(plugin_id))

    def consumer_loop(self):
        self.stream.on_recv(self.handle)

    def register_plugin(self, plugin_id):
        global PLUGIN_TIMEOUT

        (plugin_name, uuid, fqdn) = plugin_id
        now = time.time()
        registered = self.registered(plugin_id)

        if registered:
            if registered == uuid and self.expired(plugin_id):
                logging.info("Re-registering plugin due to expiry: %s@%d" % (repr(plugin_id), now))
            else:
                logging.info("Plugin registration collision: %s@%d [registered=%s]" % (repr(plugin_id), now, registered))
        else:
            logging.info("Registering plugin: %s@%d" % (repr(plugin_id), now))
            plugin_data[plugin_name] = defaultdict(dict)
            plugin_data[plugin_name][fqdn]["uuid"] = uuid

    def expired(self, plugin_id):
        (plugin_name, uuid, fqdn) = plugin_id
        return plugin_data.get(plugin_name, {}).get(fqdn, {}).get("data", {}).get("received_at", 0) < time.time() - PLUGIN_TIMEOUT

    def registered(self, plugin_id):
        (plugin_name, uuid, fqdn) = plugin_id
        return plugin_data.get(plugin_name, {}).get(fqdn, {}).get("uuid", None)
