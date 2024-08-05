#! /usr/bin/env python3

import xmlrpc
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import cv2
import pickle
from datetime import datetime, timedelta

# TODO replace with something like
# from bagelshop.picamera import PiCamera
# for a stub implementation on other platforms
from picamera import PiCamera


# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


class CameraServer:

    def __init__(self):
        self.camera = PiCamera()
        self.camera.resolution = (640, 480)
        self.last = datetime.fromtimestamp(0)
        self.sno = -1

    def get_sno(self):
        return self.sno

    def get_last_frame_stamp(self):
        return self.last.timestamp()

    def get_frame(self):
        now = datetime.now()
        fn = "/tmp/server_frame.jpg"
        if not self.last or now - self.last > timedelta(seconds=2.5):
            self.camera.capture(fn)
            self.last = now
            self.sno += 1
        img = cv2.imread(fn)
        img = cv2.rotate(img, cv2.ROTATE_180)
        return self.sno, self.last.timestamp(), \
            xmlrpc.client.Binary(pickle.dumps(img))


server = SimpleXMLRPCServer(('192.168.1.160', 8000), requestHandler=RequestHandler)
server.register_introspection_functions()
server.register_instance(CameraServer())
server.serve_forever()
