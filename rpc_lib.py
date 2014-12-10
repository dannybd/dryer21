"""
rpc_lib.py
"""

import os, sys, json, socket, functools, threading
import SocketServer

# These two functions are the API used for declaring an RPC server.
def set_rpc_socket_path(socket_path):
	global global_socket_path
	global_socket_path = socket_path

global_rpc_table = {}
def expose_rpc(function):
	global_rpc_table[function.func_name] = function

# This exception is transparently passed across the RPC boundary.
# Raise it in your handlers to signal callers.
class RPCException(Exception):
	pass

global_rpc_server_lock = threading.Lock()

class RPCRequestHandler(SocketServer.StreamRequestHandler):
	def handle(self):
		print "Opening a connection."
		while True:
			# Let exceptions happen here.
			# They will kill this handler, but be handled gracefully by SocketServer.
			line = self.rfile.readline().strip().decode("hex")
			method, kwargs = json.loads(line)
			with global_rpc_server_lock:
				print "Call to %r on %r" % (method, kwargs)
				# Look up the method in our RPC table.
				function = global_rpc_table[method]
				try:
					# Perform the actual RPC call.
					return_value = function(**kwargs)
					message = ("good", return_value)
				except RPCException, e:
					# In case of an RPC Exception, signal to the caller that something bad happened.
					message = ("bad", e.message)
				# Send message back as a JSON object over the RPC link.
				data = json.dumps(message).encode("hex")
				self.wfile.write(data + "\n")
				self.wfile.flush()

# This class is the entirety of the API for declaring an RPC client.
class RPCClient:
	def __init__(self, socket_path):
		self.socket_path = socket_path
		self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		print
		self.sock.connect(self.socket_path)
		self.sock_file = self.sock.makefile()

	def call(self, method, kwargs):
		line = json.dumps([method, kwargs]).encode("hex") + "\n"
		self.sock_file.write(line)
		self.sock_file.flush()
		response = self.sock_file.readline().strip().decode("hex")
		status, result = json.loads(response)
		if status == "good":
			return result
		elif status == "bad":
			# Transparently pass the exception through.
			raise RPCException(result)
		raise Exception("Protocol violation!")

	def make_stub(self, method):
		# Return a stub that calls into the closed-over RPC client.
		def rpc_stub(**kwargs):
			return self.call(method, kwargs)
		return rpc_stub

def launch_rpc_server(import_name):
	# Prevent a double import issue, where one copy is called __main__, and the other is rpc_lib.
	sys.modules["rpc_lib"] = sys.modules[__name__]
	# Now import the desired module, to scoop up the actual code we are offering over RPC.
	# This also has the side effect of setting global_socket_path.
	__import__(import_name)
	print "Launching RPC server: import_name=%r socket_path=%r" % (import_name, global_socket_path)
	# Unlink any socket that may exist, to make room for a new one.
	try:
		print "Deleting an old file that was in the way of our socket_path."
		os.unlink(global_socket_path)
	except OSError:
		pass
	# Now launch the server.
	print "TRYING:", os.getcwd(), global_socket_path
	server = SocketServer.ThreadingUnixStreamServer(global_socket_path, RPCRequestHandler)
	server.serve_forever()

if __name__ == "__main__":
	if len(sys.argv) == 3 and sys.argv[1] == "--launch":
		launch_rpc_server(import_name=sys.argv[2])
		exit()
	print "Usage: rpc_lib.py --launch <import>"
	print
	print "Launches an RPC server exposing every function that has expose_rpc as a"
	print "decorator in the file reached by running __import__ on the <import> argument."
