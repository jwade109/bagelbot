import xmlrpc
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import cv2
import pickle


# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


class MoDecServer:

    def __init__(self):
        self.cap = cv2.VideoCapture(0)

    def get_camera(self):
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("uh oh")
        return xmlrpc.client.Binary(pickle.dumps(frame))


server = SimpleXMLRPCServer(('127.0.0.1', 8000), requestHandler=RequestHandler)
server.register_introspection_functions()
server.register_instance(MoDecServer())
server.serve_forever()
