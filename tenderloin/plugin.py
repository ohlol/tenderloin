import ConfigParser
import json
import os
import time
import zmq

from random import randint
from uuid import uuid4


COLLECTOR_HOST = "127.0.0.1"
COLLECTOR_PORT = 49999
CONFIG_PATH = "/etc/tenderloin"


class TenderloinPlugin(object):
    def __init__(self, **kwargs):
        global COLLECTOR_HOST, COLLECTOR_PORT, CONFIG_PATH
        self.name = self.__class__.__name__.rstrip("Plugin").lower()
        self.interval = kwargs.get("interval", 60)

        config_file = kwargs.get("config_file", None)
        config_file_path = os.path.join(CONFIG_PATH, "%s.ini" % self.name)
        self.config = self.parse_config(config_file_path)

        self.worker_socket = self.get_worker_socket(kwargs.get("collector_host", COLLECTOR_HOST), kwargs.get("collector_port", COLLECTOR_PORT))

        self.id = str(uuid4())
        self.register()

    def parse_config(self, config_file):
        config = {}
        parser = ConfigParser.ConfigParser()
        parser.read(config_file)

        for section in parser.sections():
            config.setdefault(section, {})
            for option in parser.options(section):
                config[section][option] = parser.get(section, option)

        return config

    def get_data(self):
        raise NotImplementedError()

    def get_worker_socket(self, host, port):
        context = zmq.Context()
        socket = context.socket(zmq.PUSH)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.HWM, 1000)
        socket.connect("tcp://%s:%s" % (host, port))
        return socket

    def register(self):
        self.worker_socket.send(json.dumps(dict(type="register", plugin=self.name, id=self.id)))

    def loop(self):
        while True:
            self.send_msg(self.get_data())
            time.sleep(self.interval)

    def send_msg(self, msg):
        self.worker_socket.send(json.dumps(dict(type="data", plugin=self.name, data=msg)))
