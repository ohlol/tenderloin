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

    def handle(self, message):
        d = json.loads(message[0])

        if d["data"]:
            self.update_data(plugin_id=d["plugin_id"], payload=d["data"],
                             tags=d["tags"])

    def update_data(self, plugin_id, payload, tags):
        (plugin_name, uuid, fqdn) = plugin_id
        now = int(time.time())
        payload["received_at"] = now

        logging.debug("Updating plugin: %s@%d" % (repr(plugin_id), now))
        plugin_data.append(PluginData(name=plugin_name, uuid=uuid,
                                      fqdn=fqdn, tags=tags, data=payload))

    def consumer_loop(self):
        self.stream.on_recv(self.handle)
