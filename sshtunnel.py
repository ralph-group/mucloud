"""

This file is part of the MuCloud package, but is based on the
sshtunnel Python package: https://pypi.python.org/pypi/sshtunnel/

Copyright (c) 2014-2015 Colin Jermain, Graham Rowlands
Copyright (c) 2014-2015 Pahaz Blinov (sshtunnel)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

import SocketServer
import select
import threading
import logging
import paramiko


class _BaseHandler(SocketServer.BaseRequestHandler):
    remote_address = None
    ssh_transport = None
    logger = None

    def handle(self):
        assert isinstance(self.remote_address, tuple)

        try:
            chan = self.ssh_transport.open_channel(
                'direct-tcpip',
                self.remote_address,
                self.request.getpeername())
        except Exception as e:
            self.logger.error(
                "Incoming request to {0} failed: {1}".format(
                    self.remote_address, repr(e))
            )
            return
        if chan is None:
            self.logger.error(
                "Incoming request to {0} was rejected "
                "by the SSH server.".format(self.remote_address)
            )
            return

        self.logger.info('Connected!  Tunnel open.')
        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)
        chan.close()
        self.request.close()
        self.logger.info('Tunnel closed.')


class _ForwardServer(SocketServer.TCPServer):  # Not Threading
    allow_reuse_address = True

    @property
    def bind_port(self):
        return self.socket.getsockname()[1]

    @property
    def bind_host(self):
        return self.socket.getsockname()[0]


class _ThreadingForwardServer(SocketServer.ThreadingMixIn, _ForwardServer):
    daemon_threads = False


class SSHTunnelForwarder(threading.Thread):
    """
    Class for forward remote server port throw SSH tunnel to local port.

     - start()
     - stop()
     - local_bind_port
     - local_bind_host

    Example:

        >>> server = SSHTunnelForwarder(
                        ssh_address=('pahaz.urfuclub.ru', 22),
                        ssh_username="pahaz",
                        ssh_password="secret",
                        remote_bind_address=('127.0.0.1', 5555))
        >>> server.start()
        >>> print(server.local_bind_port)
        >>> server.stop()
    """

    def __init__(self,
                 ssh_address=None,
                 ssh_host_key=None,
                 ssh_username=None,
                 ssh_password=None,
                 ssh_private_key=None,
                 remote_bind_address=None,
                 local_bind_address=None,
                 threaded=False):
        """
        Address is (host, port)

        *local_bind_address* - if is None uses ("127.0.0.1", RANDOM).
        Use `forwarder.local_bind_port` for getting local forwarding port.
        """
        assert isinstance(remote_bind_address, tuple)

        if local_bind_address is None:
            # use random local port
            local_bind_address = ('', 0)

        self._local_bind_address = local_bind_address
        self._remote_bind_address = remote_bind_address
        self._ssh_private_key = ssh_private_key
        self._ssh_password = ssh_password
        self._ssh_username = ssh_username
        self._ssh_host_key = ssh_host_key

        self._transport = paramiko.Transport(ssh_address)
        self._server = self.make_server(threaded)
        self._is_started = False
        super(SSHTunnelForwarder, self).__init__()

    def make_handler(self):

        logger_ = logging.getLogger(__name__)

        class Handler(_BaseHandler):
            remote_address = self._remote_bind_address
            ssh_transport = self._transport
            logger = logger_

        return Handler

    def make_server(self, is_threaded):
        Handler = self.make_handler()
        Server = _ThreadingForwardServer if is_threaded else _ForwardServer
        server = Server(self._local_bind_address, Handler)
        return server

    def start(self):
        self._transport.connect(
            hostkey=self._ssh_host_key,
            username=self._ssh_username,
            password=self._ssh_password,
            pkey=self._ssh_private_key
        )
        super(SSHTunnelForwarder, self).start()
        self._is_started = True

    def run(self):
        self._server.serve_forever()

    def stop(self):
        if not self._is_started:
            raise Exception("Server is not started")
        self._server.shutdown()
        self._transport.close()

    @property
    def local_bind_port(self):
        if not self._is_started:
            raise Exception("Server is not started")
        return self._server.bind_port

    @property
    def local_bind_host(self):
        if not self._is_started:
            raise Exception("Server is not started")
        return self._server.bind_host
