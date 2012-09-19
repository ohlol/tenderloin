import logging
import socket
import time

from collections import defaultdict


class Carbon(object):
    def __init__(self, host, port):
        self.data = {}
        self.host = host
        self.port = port

        try:
            self.sock = self.connect()
        except socket.error:
            logging.fatal("Unable to connect to carbon")

    def connect(self, waittime=5):
        logging.info("Connecting to carbon on %s:%d" % (self.host, self.port))
        try:
            sock = socket.socket()
            sock.connect((self.host, self.port))
        except socket.error:
            logging.info("Unable to connect to carbon, retrying in %d seconds" %
                         waittime)
            time.sleep(waittime)
            self.connect(waittime + 5)

        return sock

    def _send(self, data):
        try:
            for metric, datapoints in data.items():
                for dp in datapoints:
                    logging.debug("Sending: %s %s %s" % (metric, dp[1], dp[0]))
                    self.sock.sendall("%s %s %s\n" % (metric, dp[1], dp[0]))
        except socket.error:
            raise

    def send(self):
        buf_sz = 500
        to_send = defaultdict(list)

        for metric in self.data.keys():
            while len(self.data[metric]) > 0:
                l = len(to_send)
                if l < buf_sz:
                    to_send[metric].append(self.data[metric].pop())
                else:
                    try:
                        self._send(to_send)
                    except socket.error:
                        logging.error("Error sending to carbon, trying to reconnect.")
                        self.sock = self.connect()

                        for entry in to_send:
                            self.data[entry[0]].append(entry[1])

        try:
            self._send(to_send)
        except socket.error:
            logging.error("Error sending to carbon, trying to reconnect.")
            self.sock = self.connect()

        for entry in to_send:
            self.data[entry[0]].append(entry[1])
