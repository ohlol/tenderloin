import ConfigParser
import json
import logging
import os
import socket
import time

from tornado import httpclient
from tornado.options import define, options, parse_command_line, print_help
from uuid import uuid4

CONFIG_PATH = "/etc/tenderloin"
DEFAULT_TAGS = []


class TenderloinPlugin(object):
    def __init__(self, name, tags=DEFAULT_TAGS):
        global CONFIG_PATH

        define("hostname", default=socket.getfqdn(), group="plugin",
               help="Hostname to report as")
        define("tenderloin_address", default="127.0.0.1", group="plugin",
               help="Tenderloin server address")
        define("tenderloin_port", default=50000, group="plugin",
               help="Tenderloin server port")
        define("interval", default=60, group="plugin",
               help="Plugin poll interval")

        parse_command_line()

        self.name = name
        self.config = self._parse_config(os.path.join(CONFIG_PATH, "%s.ini" %
                                                      self.name))
        self.tenderloin_url = "http://%s:%s/_send" % (options.tenderloin_address,
                                                      options.tenderloin_port)
        self.interval = options.interval
        self.whoami = (self.name, str(uuid4()), options.hostname)
        self.tags = set(tags) | set([self.whoami[0], self.whoami[2]])
        self._metrics = {}

    def __contains__(self, metric):
        return metric in self._metrics

    def __iter__(self):
        for metrics in self._metrics.items():
            yield metrics

    def __setitem__(self, key, value):
        f = lambda x: x.replace(".", "_").replace(" ", "_")
        self._metrics[f(key)] = self._sanitize_keys(f, value)

    def __getitem__(self, key):
        return self._metrics[key]

    def _parse_config(self, config_file):
        config = {}
        parser = ConfigParser.ConfigParser()
        parser.read(config_file)

        for section in parser.sections():
            config.setdefault(section, {})
            for option in parser.options(section):
                config[section][option] = parser.get(section, option)

        return config

    def _handle_response(self, response):
        if response.error:
            logging.error("Could not POST to tenderloin server: %s" %
                          response.error)

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
        http = httpclient.HTTPClient()
        http.fetch(self.tenderloin_url,
                   method="POST",
                   headers={"Content-Type": "application/json"},
                   body=json.dumps(dict(plugin_id=self.whoami,
                                        tags=list(self.tags),
                                        data=msg)))
