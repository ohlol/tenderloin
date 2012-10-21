import logging
import socket
import time

from collections import defaultdict


class Carbon(object):
    def __init__(self, host, port):
        self.data = []
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
            for metric in data:
                logging.debug("Sending %s" % metric)
            self.sock.sendall("\n".join(data))
        except socket.error:
            raise

    def send(self):
        buf_sz = 500
        to_send = []

        while len(to_send) < buf_sz and self.data:
            to_send.append(self.data.pop())

        try:
            self._send(to_send)
        except socket.error:
            logging.error("Error sending to carbon, trying to reconnect.")
            self.sock = self.connect()

            for metric in to_send:
                self.data.append(metric)
