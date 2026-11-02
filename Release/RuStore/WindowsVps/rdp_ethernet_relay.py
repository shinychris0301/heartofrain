"""Forward a local RDP socket over a selected Ethernet source address.

The relay binds to loopback only. It forwards encrypted RDP bytes unchanged
and never records credentials or traffic. Stop the process to close the relay.
"""

import argparse
import ipaddress
import select
import socket
import socketserver

VPS = ("178.22.24.247", 3389)


class Relay(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as upstream:
            upstream.bind((self.server.source_ip, 0))
            upstream.settimeout(8)
            upstream.connect(VPS)
            upstream.settimeout(None)
            downstream = self.request
            while True:
                readable, _, _ = select.select((downstream, upstream), (), ())
                for source in readable:
                    payload = source.recv(65536)
                    if not payload:
                        return
                    (upstream if source is downstream else downstream).sendall(payload)


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = 4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-ip", required=True)
    parser.add_argument("--listen-port", type=int, default=13389)
    args = parser.parse_args()
    source = ipaddress.IPv4Address(args.source_ip)
    if source.is_loopback or source.is_unspecified or source.is_multicast:
        parser.error("An active Ethernet IPv4 address is required")
    if not 1024 <= args.listen_port <= 65535:
        parser.error("The local port must be unprivileged")
    with Server(("127.0.0.1", args.listen_port), Relay) as server:
        server.source_ip = str(source)
        server.serve_forever(poll_interval=0.25)


if __name__ == "__main__":
    main()
