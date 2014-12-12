"""
Dryer21Client.py

Provides a client for communicating with the Dryer 21 bond seller server.

To run the client with its interface, run:
	$ python Dryer21Client.py [--nosave] [--mock] [--bypasstor]
or:
	$ python
	>>> from Dryer21Client import *
	>>> run_client

If you would rather run the steps manually, here's what you need to run to
generate a bond:
	$ python
	>>> from Dryer21Client import *
	>>> token = gen_token(); token
	>>> price, addr = fetch_quote(token)
	>>> print 'Go pay', price, 'to', addr
	>>> # When that's done and confirmed:
	>>> protobond = fetch_protobond(token); protobond
	>>> bond = gen_bond(protobond); bond
	>>> validate_bond(bond)
	>>> print 'Valid bond!'
	>>> # Store the bond to a file
	>>> filename = save_bond(bond)
	>>> print 'Your bond is stored here:', filename

"""
import Crypto.Util.number as CryptoNumber
import Crypto.Cipher.PKCS1_OAEP as PKCS1_OAEP
import Crypto.Hash.SHA512 as SHA512
import Crypto.PublicKey.RSA as RSA
import base64, json, random, os, sys, time, urllib

save, mock, bypassTor = True, False, False
BASE_URL = 'http://dryer4xxsgccsbec.onion/'
MOCK_BASE_URL = 'http://127.0.0.1:9001/'

def fetch_connect():
	""" Initial connectivity test to the server. """
	data = load_url(path='connect')
	return bool(data['success'])

def gen_token():
	"""
	Generates a token, which is of the form (m*r^e) mod n.
	Contains a message, m, which is of the form OAEP(PREFIX || Hash(n, x) || x),
	as well as a nonce, r, which is encrypted. The nonce is stored for final
	bond generation later.
	"""
	# Generate x, which is random with a prefix for verification purposes
	x = CryptoVars.x_prefix + os.urandom(CryptoVars.x_entropy_bytes)
	# h = Hash(n, x)
	h = hash(CryptoNumber.long_to_bytes(CryptoVars.n), x)
	# m = OAEP(PREFIX || Hash(n, x) || x)
	m = OAEP(CryptoVars.msg_prefix + h + x)
	# Convert to a long mod n
	m = CryptoNumber.bytes_to_long(m)
	if m != (m % CryptoVars.n):
		raise ValueError('OAEP_cipher._key.n > key.n causing invalid m')
	# Generate the nonce, r, such that 0 <= r < n
	# The nonce is stored for later use for turning the protobond into a bond
	CryptoVars.nonce = random.SystemRandom().randint(0, CryptoVars.n - 1)
	# Generate (r^e) mod n
	nonce_e = encrypt(CryptoVars.nonce)
	# Token = (m*r^e) mod n
	token = (m * nonce_e) % CryptoVars.n
	# Encode for sending to server / display to user
	return long_encode(token)

def fetch_quote(token):
	"""
	Sending up a token returns a quote to the user, containing the current cost
	of a bond (fluctating with transaction fees) and a Bitcoin address where
	the user should send their Bitcoin.
	"""
	data = load_url(path='quote', data={'token': token})
	return (data['price'], data['addr'])

def fetch_protobond(token):
	"""
	Checks the server to see whether the bitcoin has come in yet: if it has,
	then the server responds with the protobond = (m*r^e)^d = (m^d * r).
	If the client is mocking out the response, then pretend to generate the
	protobond and return that instead.
	"""
	data = load_url(path='protobond', data={'token': token})
	return data.get('protobond', None)

def gen_bond(protobond):
	"""
	Given the encoded version of the long which represents the protobond,
	convert it back into a long, and multiply it by nonce_inv to get the bond.
	"""
	protobond = long_decode(protobond)
	# Generate nonce's inverse, r^-1, from the stored nonce
	nonce_inv = CryptoNumber.inverse(CryptoVars.nonce, CryptoVars.n)
	# BOND = (PROTOBOND * r^-1) = (m^d * r * r^-1) = (m^d) mod n
	bond = (protobond * nonce_inv) % CryptoVars.n
	# Encode the long for storage / display to the user
	return long_encode(bond)

def validate_bond(bond):
	"""
	Bond validation needs to happen server-side, but there's not reason why the
	client can't also verify that they have received a valid bond.
	BOND = m^d, m = OAEP(PREFIX || Hash(n, x) || x).
	"""
	# Make sure the bond holds a number
	bond = long_decode(bond)
	# BOND^E = m^d^e = m
	msg = CryptoNumber.long_to_bytes(encrypt(bond))
	# Since OAEP is all-or-nothing, we need to restore the leading zero bytes
	msg = msg.rjust(CryptoVars.OAEP_cipher_len, chr(0))
	# Try to decrypt OAEP format --> (PREFIX || Hash(h, x) || x)
	try:
		msg = inverse_OAEP(msg)
	except ValueError, e:
		print 'Not a valid bond: OAEP failure'
		raise e
	# Check for PREFIX
	if not msg.startswith(CryptoVars.msg_prefix):
		raise ValueError('Not a valid bond: msg_prefix failure')
	# Extract h = Hash(n, x) and x
	msg = msg[len(CryptoVars.msg_prefix):]
	h = msg[:-CryptoVars.x_len]
	x = msg[-CryptoVars.x_len:]
	# Check for x's prefix
	if not x.startswith(CryptoVars.x_prefix):
		raise ValueError('Not a valid bond: x_prefix failure')
	# Make sure that the hash is in fact Hash(n, x)
	if h != hash(CryptoNumber.long_to_bytes(CryptoVars.n), x):
		raise ValueError('Not a valid bond: hash failure')
	# Huzzah! It's valid!
	return True

def save_bond(bond):
	"""
	Create a random 16-byte hex filename with a .bond extension, store the
	bond there, and return the filename.
	"""
	filename = os.urandom(16).encode('hex').upper() + '.bond'
	if mock:
		filename = 'mock-' + filename
	with open(filename, 'w+') as f:
		f.write(bond)
	return filename

def run_client():
	"""Runs the interface for bond purchasing."""
	print
	print 'Now running: Dryer 21 Client Script'
	if mock:
		print 'ENTERING MOCK MODE'
	# Connect to server and pull relevant variables
	printf('Testing connection to Dryer 21 server.....')
	fetch_connect()
	print 'Done.'
	# Generate a token based on those variables
	printf('Generating token.....')
	token = gen_token()
	print 'Done.'
	# Get the bond quote
	printf('Sending token to server.....')
	price, addr = fetch_quote(token)
	print 'Done.'
	print
	print 'You have successfully submitted a token to the server.'
	print 'To purchase the bond, please send ' + str(price) + ' satoshi to this address: ' + addr
	print
	# Time to wait between server checks, in seconds
	check_period = 10
	print 'Checking for protobond every ' + str(check_period) + ' seconds:'
	# Ask the server for the protobond
	protobond = fetch_protobond(token)
	while protobond == None:
		printf('Bitcoin not yet received. Waiting.....')
		# Draw periods until time to check again
		for i in range(check_period):
			time.sleep(1)
			printf('.')
		print
		# Ask again for the protobond
		protobond = fetch_protobond(token)
	print 'Transaction cleared!'
	print
	# Generate the bond with the received protobond
	printf('Generating bond.....')
	bond = gen_bond(protobond)
	# The nonce should be destroyed at this stage; it's not needed anymore
	del CryptoVars.nonce
	print 'Done.'
	# Validate the bond
	printf('Validating bond.....')
	validate_bond(bond)
	print 'Done.'
	if save:
		# Save the bond to a .bond file in the current directory.
		printf('Saving bond.....')
		filename = save_bond(bond)
		print 'Done.'
		print
		print
		print 'Congrats! You have successfully purchased a bond. It has been stored here:'
		print
		print os.path.join(os.path.abspath('.'), filename)
	else:
		print
		print
		print 'Congrats! You have successfully purchased a bond. Here it is:'
		print
		print bond
	print
	print 'Remember to wait a few days before trying to redeem your bond.'
	print 'Thank you for using Dryer 21!'
	print

def printf(s):
	""" Print to the display without the automatic new line. """
	sys.stdout.write(s)
	sys.stdout.flush()

def load_url(path, data={}):
	"""
	Load a URL (optionally with data) via POST, and return the JSON object at
	that URL. Throws errors on connection failures or JSON errors in the response.
	"""
	if mock:
		url = MOCK_BASE_URL + path
	else:
		url = BASE_URL + path
	if bypassTor:
		from urllib2 import urlopen
		response = urlopen(url, urllib.urlencode(data))
	else:
		response = urlopen_with_tor(url, urllib.urlencode(data))
	return json.load(response)

def urlopen_with_tor(*args, **kwargs):
	""" Wraps around urllib2.urlopen that passes the request through tor """
	import socks
	import socket
	import urllib2
	# Use Tor's SOCKS5 server running on port 9150
	socks.setdefaultproxy(socks.SOCKS5, 'LOCALHOST', 9150, rdns=True)
	# The following is necessary to keep urllib2.urlopen from leaking DNS.
	# Torify ALL the sockets!
	socket.socket = socks.socksocket
	def create_connection(address, timeout=None, source_address=None):
		sock = socks.socksocket()
		sock.connect(address)
		return sock
	socket.create_connection = create_connection
	# Now all sockets we open will use Tor.
	return urllib2.urlopen(*args, **kwargs)

def hash(*args):
	""" Update a SHA512 hash with one argument at a time, then return it """
	h = SHA512.new()
	for arg in args:
		h.update(arg)
	return h.digest()

def OAEP(s):
	"""
	Encrypt a string using OAEP and the OAEP cipher stored above. Note that this
	does NOT use the main RSA encryption used for token and bond generation.
	"""
	# OAEP can only encrypt 382 bytes of input with a 4096-bit RSA key.
	if len(s) > 382:
		raise NameError('OAEP input is too long (>382 bytes)')
	encrypted = CryptoVars.OAEP_cipher.encrypt(s)
	if len(encrypted) != CryptoVars.OAEP_cipher_len:
		raise ValueError('OAEP cipher length is incorrect')
	return encrypted

def inverse_OAEP(s):
	"""
	Decrypt a string using OAEP and the OAEP cipher stored above. Note that this
	does NOT use the main RSA encryption used for token and bond generation.
	"""
	return CryptoVars.OAEP_cipher.decrypt(s)

def encrypt(s):
	""" Wrapper around the encryption used by Crypto.PublicKey.RSA._RSAobj """
	# (the second argument is ignored, according to PyCrypto docs)
	return CryptoVars.key.encrypt(s, 0)[0]

def long_encode(n):
	""" Encodes a long in a base64 string which is easily sendable / storable """
	return base64.b64encode(hex(n))

def long_decode(s):
	""" Decodes a base64 string (formed by long_encode) into a long """
	return long(base64.b64decode(s), 16)

def import_key(keystr):
	""" Create a key from a base64-encoded string defining an RSA key """
	return RSA.importKey(base64.b64decode(keystr))

class CryptoVars:
	""" Stores the variables involved within the crypto processes. """
	# key, n correspond to the 4096-bit RSA used in the token and bond
	keystr = {{ '%r'|format(CryptoVars.keystr) }}
	key = import_key(keystr)
	n = key.n
	# OAEP_cipher is also based on 4096-bit RSA, and contains both the public
	# and private key. This is NOT used for encrypting the token or bond, but
	# instead to encrypt and descrypt the message [OAEP(Hash(n, x) || x)].
	# We're using PyCrypto for our encryption, and it only provides OAEP as part
	# of PKCS1_OAEP, which requires an encryption scheme. By providing the private
	# key of the OAEP_cipher publicly, we annul the encryption part of the cipher
	# but maintain OAEP's all-or-nothing attribute.
	OAEP_keystr = {{ '%r'|format(CryptoVars.OAEP_keystr) }}
	OAEP_key = import_key(OAEP_keystr)
	OAEP_cipher = PKCS1_OAEP.new(OAEP_key, SHA512)
	# Length of resulting OAEP-encrypted message
	OAEP_cipher_len = {{ '%r'|format(CryptoVars.OAEP_cipher_len) }}
	# The seed of the message, x, is given a recognizable prefix for further
	# validation purposes
	x_prefix = {{ '%r'|format(CryptoVars.x_prefix) }}
	x_entropy_bytes = {{ '%r'|format(CryptoVars.x_entropy_bytes) }}
	x_len = x_entropy_bytes + len(x_prefix)
	# The message, m, is also given a prefix, for providing a first-step
	# validation with a high degree of confidence that this is an actual signed
	# bond
	msg_prefix = x_prefix
	# Holds the nonce for generating the bond from the protobond.
	# Needs to be destroyed after use, so we're storing it as a value here and not
	# passing it as an argument between frames to minimize copies in memory.
	nonce = None

if __name__ == '__main__':
	save = '--nosave' not in sys.argv[1:]
	mock = '--mock' in sys.argv[1:]
	bypassTor = '--bypasstor' in sys.argv[1:]
	run_client()
