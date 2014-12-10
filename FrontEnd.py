"""
FrontEnd

Handles connections from clients.
"""

import socket
import SocketServer
import BaseHTTPServer
import time

time.sleep(1)

from rpc_clients import Database

class Dryer21Server(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
	def server_bind(self):
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		BaseHTTPServer.HTTPServer.server_bind(self)

class Dryer21Handler(BaseHTTPServer.BaseHTTPRequestHandler):
	def do_GET(s):
		#
		s.send_response(200)
		s.send_header("Content-type", "text/plain")
		s.end_headers()
		s.wfile.write("I got the data: %s" % s.path)

if __name__ == "__main__":
	print "Launching front end server."
	Dryer21Server(("", 8080), Dryer21Handler).serve_forever()

