import json
import logging
import time
import zmq

from collections import defaultdict
from zmq.eventloop import zmqstream

from tenderloin.listeners import plugin_data

PLUGIN_TIMEOUT = 300


class PluginData(object):
    def __init__(self, name, uuid, fqdn, tags, data):
        self.name = name
        self.uuid = uuid
        self.fqdn = fqdn
        self.tags = tags
        self.data = data


class MessageListener(object):
    def __init__(self, address, port):
        context = zmq.Context()
        socket = context.socket(zmq.PULL)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.HWM, 1000)
        logging.info("Starting up message listener on %s:%d", address, port)
        socket.bind("tcp://%s:%s" % (address, port))
        self.stream = zmqstream.ZMQStream(socket)

    def find(self, f, seq):
        """Return first item in sequence where f(item) == True."""
        """h/t http://tomayko.com/writings/cleanest-python-find-in-list-function"""
        for item in seq:
            if f(item):
                return item

    def handle(self, message):
        d = json.loads(message[0])

        if d["data"]:
            self.update_data(plugin_id=d["plugin_id"], payload=d["data"],
                             tags=d["tags"])

    def update_data(self, plugin_id, payload, tags):
        (plugin_name, uuid, fqdn) = plugin_id
        now = int(time.time())
        payload["received_at"] = now

        self.register_plugin(plugin_id, tags)

        if self.registered(plugin_id):
            logging.debug("Updating plugin: %s@%d" % (repr(plugin_id), now))
            plugin_data.append(PluginData(name=plugin_id[0], uuid=plugin_id[1],
                                          fqdn=plugin_id[2], tags=tags,
                                          data=payload))
        else:
            logging.info("Ignoring plugin data due to registration "
                         "collision: %s" % repr(plugin_id))

    def consumer_loop(self):
        self.stream.on_recv(self.handle)

    def register_plugin(self, plugin_id, tags):
        global PLUGIN_TIMEOUT

        (plugin_name, uuid, fqdn) = plugin_id
        now = time.time()
        registered = self.registered(plugin_id)

        if registered:
            if registered == uuid:
                if  self.expired(plugin_id):
                    logging.info("Re-registering plugin due to expiry: %s@%d" %
                                 (repr(plugin_id), now))
            else:
                logging.info("Plugin registration collision: %s@%d "
                             "[registered=%s]" %
                             (repr(plugin_id), now, registered))
        else:
            logging.info("Registering plugin: %s@%d [tags=%s]" %
                         (repr(plugin_id), now, repr(tags)))

    def expired(self, plugin_id):
        return self.find(lambda plugin:
                         plugin_id, plugin_data).data.get("received_at", 0) <\
            time.time() - PLUGIN_TIMEOUT

    def registered(self, plugin_id):
        p = self.find(lambda plugin: (plugin.name, plugin.uuid, plugin.fqdn) ==
                      plugin_id, plugin_data)

        if hasattr(p, 'uuid'):
            return plugin_id[1] == p.uuid
        else:
            return True
