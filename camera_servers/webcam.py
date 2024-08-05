#! /usr/bin/env python3

import xmlrpc
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import cv2
import pickle
from datetime import datetime
import sys


# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


ipaddr = sys.argv[1]
port = int(sys.argv[2])


class CameraServer:

    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.last = datetime.fromtimestamp(0)
        self.sno = -1

    def get_sno(self):
        return self.sno

    def get_last_frame_stamp(self):
        return self.last.timestamp()

    def get_frame(self):
        _, img = self.cap.read()
        self.sno += 1
        return self.sno, datetime.now(), xmlrpc.client.Binary(pickle.dumps(img))


server = SimpleXMLRPCServer((ipaddr, port), requestHandler=RequestHandler)
server.register_introspection_functions()
server.register_instance(CameraServer())
server.serve_forever()
