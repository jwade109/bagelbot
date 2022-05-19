#! /usr/bin/env python3

from xmlrpc.server import SimpleXMLRPCServer
import socket

def getip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def fib(n):
    if n < 1:
        return 0
    if n == 1:
        return 1
    return fib(n-1) + fib(n-2)

ip_addr = getip()

print(f"Your IP is {ip_addr}")

server = SimpleXMLRPCServer((ip_addr, 8000))

server.register_introspection_functions()

server.register_function(socket.gethostname)
server.register_function(getip)
server.register_function(fib)

server.serve_forever()