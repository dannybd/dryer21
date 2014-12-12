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
	keystr = 'MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEApYV26Umk/uU0Gau29/XNKhxtA1P6fwhMctW+5Jqg32tYwVk2ZUMGHzgDexZdHmOoHYFYllP1TuWZEMpTwxMCJtV0gWhBGdUmAECVnVwmzfG2RvCfVSlmbNei2C6I2mlC05eg0tXyGW4AGXG8yfhW/P2mD23B7zZGzY8/thCWCYGnbNG9i0+Qk4muohLyoLhIGcHK38yDmsjQ3JFSSwrg2S6iXa/dfXbPonNZZvSZAUYBeRaZoJYtmD8hygQSy++HQ254las1UtTLlvdLZ9O6vIg6y0vCSjWn1NCqAYlm94mFxk9cIB9iIkmES37sLZMG8YD47xCxiLAcIxpwoVJJVrIc+wQoT4qNSdCixQG0Z7HA7+DcWA1txFSH8zaTmCI0AKL5zxSsitzprB8TJcaDAFq7DXUW1LuysnEEdm+Nf20MLZ/pwjJu4lMkP0K/ukdt0VHXSjNYZkhUEwUju3T0W10ZzdCjL3AdjnPBw/CMaCOaXxjsN/9qhH59p8+FmFUu749mp6j+5u25o93SEnPy8xDbf6wNjueU2a4z10u4o16frfIEwz84peGKeamGH9ALLV3nlC+bVd7AhE3MfXQ/B1YJUxPVhmYkKJvkRcBTpZMIGhzVG5PwTLxS1GDz0mhoBkic8RDVN6fVpkEutA9nZGgKFBL+u+rPa5JjSLwP3mcCAwEAAQ=='
	key = import_key(keystr)
	n = key.n
	# OAEP_cipher is also based on 4096-bit RSA, and contains both the public
	# and private key. This is NOT used for encrypting the token or bond, but
	# instead to encrypt and descrypt the message [OAEP(Hash(n, x) || x)].
	# We're using PyCrypto for our encryption, and it only provides OAEP as part
	# of PKCS1_OAEP, which requires an encryption scheme. By providing the private
	# key of the OAEP_cipher publicly, we annul the encryption part of the cipher
	# but maintain OAEP's all-or-nothing attribute.
	OAEP_keystr = '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'
	OAEP_key = import_key(OAEP_keystr)
	OAEP_cipher = PKCS1_OAEP.new(OAEP_key, SHA512)
	# Length of resulting OAEP-encrypted message
	OAEP_cipher_len = 512
	# The seed of the message, x, is given a recognizable prefix for further
	# validation purposes
	x_prefix = '[[BITCOIN BOND]]'
	x_entropy_bytes = 256
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
