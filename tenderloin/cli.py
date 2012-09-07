from tornado.options import define, options, parse_command_line

from tenderloin.server import Server


def server():
    define("listen_address", default="127.0.0.1", help="Bind to address")
    define("listen_port", default=50000, help="Web server listen port")

    parse_command_line()
    server = Server(options.listen_address, options.listen_port - 1,
                    options.listen_port)
