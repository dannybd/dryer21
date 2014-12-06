"""
torsocket.py: Provides methods for making connections through tor.
"""
import socks
import socket

def starttor():
	print "torsocket.starttor: NOT IMPLEMENTED YET"
	pass

def urlopen(url):
	"""
		urlopen: a wrapper around urllib2.urlopen that passes the request through tor.
	"""
	socks.setdefaultproxy(socks.SOCKS5, "localhost", 9150, rdns=True) # Use Tor's SOCKS5 server running on port 9150
	# The following is necessary to keep urllib2.urlopen from leaking DNS
	socket.socket = socks.socksocket # Torify ALL the sockets!
	def create_connection(address, timeout=None, source_address=None):
		sock = socks.socksocket()
		sock.connect(address)
		return sock
	socket.create_connection = create_connection
	# Now all sockets we open will use Tor.
	return urllib2.urlopen(url)
