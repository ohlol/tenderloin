import tornado
import zmq

from zmq.eventloop import ioloop

from tenderloin.listeners.message import MessageListener
from tenderloin.listeners.web import WebListener


class Server(object):
    def __init__(self, listen_address=None, message_port=49999,
                 web_port=50000):
        ioloop.install()
        ml = MessageListener(listen_address, message_port)
        ml.consumer_loop()

        wl = WebListener(listen_address, web_port)
        wl.start()
        tornado.ioloop.IOLoop.instance().start()
