import ConfigParser
import json
import os
import socket
import time
import zmq

from uuid import uuid4

COLLECTOR_HOST = "127.0.0.1"
COLLECTOR_PORT = 49999
CONFIG_PATH = "/etc/tenderloin"
DEFAULT_TAGS = []


class TenderloinPlugin(object):
    def __init__(self, name, interval=60, collector_host=COLLECTOR_HOST,
                 collector_port=COLLECTOR_PORT, tags=DEFAULT_TAGS):
        global COLLECTOR_HOST, COLLECTOR_PORT, CONFIG_PATH

        self.name = name
        self.interval = interval
        self.config = self._parse_config(os.path.join(CONFIG_PATH, "%s.ini" %
                                                      self.name))
        self.whoami = (self.name, str(uuid4()), socket.getfqdn())
        self.tags = set(tags) | set([self.whoami[0], self.whoami[2]])
        self._worker_socket = self._get_worker_socket(collector_host,
                                                      collector_port)
        self._metrics = {}

    def __iter__(self):
        for metrics in self._metrics.items():
            yield metrics

    def __setitem__(self, key, value):
        f = lambda x: x.replace(".", "_").replace(" ", "_")
        self._metrics[f(key)] = self._sanitize_keys(f, value)

    def __getitem__(self, key):
        return self._metrics[key]

    def _sanitize_keys(self, func, data):
        if isinstance(data, dict):
            for k, v in data.items():
                del data[k]
                if isinstance(v, dict):
                    data[func(k)] = self._sanitize_keys(func, v)
                else:
                    data[func(k)] = v
            return data
        elif isinstance(data, str):
            return func(data)
        else:
            return data

    def _parse_config(self, config_file):
        config = {}
        parser = ConfigParser.ConfigParser()
        parser.read(config_file)

        for section in parser.sections():
            config.setdefault(section, {})
            for option in parser.options(section):
                config[section][option] = parser.get(section, option)

        return config

    def _get_worker_socket(self, host, port):
        context = zmq.Context()
        socket = context.socket(zmq.PUSH)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.HWM, 1000)
        socket.connect("tcp://%s:%s" % (host, port))

        return socket

    def get_data(self):
        raise NotImplementedError()

    def loop(self):
        while True:
            payload = {}
            self.get_data()
            for x, y in self:
                payload[x] = y
            self.send_msg(payload)
            time.sleep(self.interval)

    def send_msg(self, msg):
        self._worker_socket.send(json.dumps(dict(plugin_id=self.whoami,
                                                 tags=list(self.tags),
                                                 data=msg)))
