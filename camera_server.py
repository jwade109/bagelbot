import xmlrpc
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler


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

    def get_frame(self):
        fn = "/tmp/server_frame.jpg"
        self.camera.capture(fn)
        return xmlrpc.client.Binary(open(fn, "rb").read())


server = SimpleXMLRPCServer(('127.0.0.1', 8000), requestHandler=RequestHandler)
server.register_introspection_functions()
server.register_instance(CameraServer())
server.serve_forever()
