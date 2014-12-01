from base64 import b64encode, b64decode
import Crypto.Util.number as CryptoNumber
import Crypto.Cipher.PKCS1_OAEP as PKCS1_OAEP
import Crypto.Hash.SHA512 as SHA512
import Crypto.PublicKey.RSA as RSA
import json
import os
import sys
from time import sleep
from urllib import urlencode
from urllib2 import urlopen

class DryerServer:
	"""
	Handles connections to the server, and interpretations of the responses.
	"""
	BASE_URL = 'http://dannybd.mit.edu/6.858/'
	INIT_URL = 'fetch_crypto_vars.php'
	TOKEN_URL = 'fetch_quote.php'
	PROTOBOND_URL = 'fetch_protobond.php'
	LEGAL_URLS = [INIT_URL, TOKEN_URL, PROTOBOND_URL]

	errmsg = 'Unable to connect to server. Please connect and try again.'

	@staticmethod
	def load(url, data={}, errmsg=errmsg):
		"""
		Load a URL (optionally with data) via POST, and return the JSON object at
		that URL. Throws errors on connection failures, bad URLs, or JSON errors in
		the response.
		"""
		if url not in DryerServer.LEGAL_URLS:
			raise ValueError('Need to use a valid URL')
		try:
			response = urlopen(DryerServer.BASE_URL + url, urlencode(data))
		except Exception:
			Interface.failWaiting(errmsg)
		try:
			return json.load(response)
		except ValueError:
			Interface.failWaiting('JSON error in returned data.')

	@staticmethod
	def fetchCryptoVars():
		"""
		Load the crypto variables stored on the server which are needed for running
		the operation. Generate the relevant keys from the transported data. This
		also serves as an initial connectivity test to the server.
		"""
		data = DryerServer.load(DryerServer.INIT_URL)
		(key, n) = CryptoHelper.importKey(data['key'])
		OAEP_key = CryptoHelper.importKey(data['OAEP_key'])[0]
		return (key, n, data['k'], OAEP_key)

	@staticmethod
	def fetchQuote(token):
		"""
		Sending up a token returns a quote to the user, containing the current cost
		of a bond (fluctating with transaction feeds) and a Bitcoin address where
		the user should send their Bitcoin.
		"""
		data = DryerServer.load(
			DryerServer.TOKEN_URL,
			data={'token': token},
			errmsg='Unable to send token to server. Please connect and try again.',
		)
		if 'error' in data:
			print 'Error occurred fetching price and addr:', data['error']
			return (None, None)
		return (data['price'], data['addr'])

	@staticmethod
	def fetchProtobond(token):
		"""
		Checks the server to see whether the bitcoin has come in yet: if it has,
		then the server responds with the protobond = (m*r^e)^d = (m^d * r).
		If the client is mocking out the response, then pretend to generate the
		protobond and return that instead.
		"""
		data = DryerServer.load(
			DryerServer.PROTOBOND_URL,
			data={'token': token},
			errmsg='Unable to check server for protobond. Please connect and try again.',
		)
		protobond = data.get('protobond', None)
		if protobond and Interface.mock:
			protobond = CryptoServer.genProtobond(token)
		return protobond

class CryptoVars:
	"""
	Stores the variables involved within the crypto processes. Also has a method
	for destroying the nonce_inv when it is no longer needed.
	"""
	# key, n correspond to the 4096-bit RSA used in the token and bond
	key = None
	n = None
	# k is a publicly-known value used to mix with the hash in token generation
	k = None
	# OAEP_cipher is also based on 4096-bit RSA, and contains both the public
	# and private key. This is NOT used for encrypting the token or bond, but
	# instead to encrypt and descrypt the message [OAEP(Hash, k, x) || x)].
	# We're using PyCrypto for our encryption, and it only provides OAEP as part
	# of PKCS1_OAEP, which requires an encryption scheme. By providing the private
	# key of the OAEP_cipher publicly, we annul the encryption part of the cipher
	# but maintain OAEP's all-or-nothing attribute.
	OAEP_cipher = None
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
	# Holds the inverse of the nonce, for generating the bond from the protobond.
	# Needs to be destroyed after use, so we're storing it as a value here and not
	# passing it as an argument between frames to minimize copies in memory.
	nonce_inv = None

	@staticmethod
	def init(key, n, k, OAEP_key):
		"""
		Sets the crypto variables which have been pulled from the server. Also
		generates the OAEP cipher directly from the key.
		"""
		CryptoVars.key = key
		CryptoVars.n = n
		CryptoVars.k = k
		CryptoVars.OAEP_cipher = PKCS1_OAEP.new(OAEP_key, SHA512)

	@staticmethod
	def destroyNonceInv():
		"""
		The nonce's inverse should be destroyed after use, so we attempt that here.
		We overwrite the variable's value, then delete it. This isn't perfect, but
		this part doesn't need to be perfect, only make it much more difficult to
		recover the nonce inverse.
		"""
		CryptoVars.nonce_inv = int(os.urandom(256).encode('hex'), 16)
		del CryptoVars.nonce_inv

class CryptoHelper:
	"""
	A class of helper methods for making the crypto work.
	"""
	@staticmethod
	def importKey(keystr):
		"""
		From a base64-encoded string defining an RSA key, create the key and its n.
		"""
		key = RSA.importKey(b64decode(keystr))
		return (key, key.n)

	@staticmethod
	def hash(*args):
		"""
		Update a new SHA512 hash with one argument at a time, and return that hash.
		"""
		h = SHA512.new()
		for arg in args:
			h.update(arg)
		return h.digest()

	@staticmethod
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
			raise ValueError('OAEP cipher length is incorrect. Please try again.')
		return encrypted

	@staticmethod
	def deOAEP(s):
		"""
		Decrypt a string using OAEP and the OAEP cipher stored above. Note that this
		does NOT use the main RSA encryption used for token and bond generation.
		"""
		return CryptoVars.OAEP_cipher.decrypt(s)

	@staticmethod
	def genNonce():
		"""
		Generate the nonce, r, for the message. We don't actually need the nonce
		itself: its inverse, (r^-1) mod n, is stored for generating the bond from
		the protobond later, and r^e is returned for using in token generation.
		"""
		nonce = CryptoNumber.getRandomRange(0, CryptoVars.n)
		# The inverse of the nonce is stored for later use as protobond --> bond
		CryptoVars.nonce_inv = CryptoNumber.inverse(nonce, CryptoVars.n)
		nonce_e = CryptoHelper.encrypt(nonce)
		# Destroy the nonce as it is no longer needed.
		nonce = int(os.urandom(256).encode('hex'), 16)
		del nonce
		return nonce_e

	@staticmethod
	def encrypt(s):
		"""
		Wrapper around the encryption method used by Crypto.PublicKey.RSA._RSAobj
		"""
		return CryptoVars.key.encrypt(s, 0)[0]

	@staticmethod
	def bytesToLong(s):
		"""
		Wrapper around the bytestring-->long method in Crypto.Util.number
		"""
		return CryptoNumber.bytes_to_long(s)

	@staticmethod
	def longToBytes(n):
		"""
		Wrapper around the long-->bytestring method in Crypto.Util.number
		"""
		return CryptoNumber.long_to_bytes(n)

	@staticmethod
	def longEncode(n):
		"""
		Encodes a long in a base64 string which is easily sendable / storable
		"""
		return b64encode(hex(n))

	@staticmethod
	def longDecode(s):
		"""
		Decodes a base64 string (formed by longEncode) into a long
		"""
		return long(b64decode(s), 16)

class CryptoClient:
	"""
	Provides methods which define actions performed client-side to purchase a
	bitcoin bond.
	"""
	@staticmethod
	def genCryptoVars():
		"""
		Pulls required variables from the server and populates CryptoVars class
		"""
		CryptoVars.init(*DryerServer.fetchCryptoVars())

	@staticmethod
	def genToken():
		"""
		Generates a token, which is of the form (m*r^e) mod n.
		Contains a message, m, which is of the form OAEP(PREFIX || Hash(k, x) || x),
		as well as a nonce, r, which is encrypted. The nonce's inverse is generated
		and stored for final bond generation later.
		"""
		# Generate x, which is random with a prefix for verification purposes
		x = CryptoVars.x_prefix + os.urandom(CryptoVars.x_entropy_bytes)
		# h = Hash(k, x) [k is supplied by the server]
		h = CryptoHelper.hash(CryptoVars.k, x)
		# m = OAEP(PREFIX || Hash(k, x) || x)
		m = CryptoHelper.OAEP(CryptoVars.msg_prefix + h + x)
		# Convert to a long mod n
		m = CryptoHelper.bytesToLong(m)
		if m != (m % CryptoVars.n):
			raise ValueError('m is too big!')
		# Generate (r^e) mod n, also (r^-1) mod n [stored as CryptoVars.nonce_inv]
		nonce_e = CryptoHelper.genNonce() % CryptoVars.n
		# Token = (m*r^e) mod n
		token = (m * nonce_e) % CryptoVars.n
		# Encode for sending to server / display to user
		return CryptoHelper.longEncode(token)

	@staticmethod
	def genBond(protobond_str):
		"""
		Given the encoded version of the long which represents the protobond,
		convert it back into a long, and multiply it by nonce_inv to get the bond.
		"""
		protobond = CryptoHelper.longDecode(protobond_str)
		# BOND = (PROTOBOND * r_inv) = (m^d * r * r_inv) = (m^d) mod n
		bond = (protobond * CryptoVars.nonce_inv) % CryptoVars.n
		# The nonce_inv should be destroyed at this stage; it's not needed anymore
		CryptoVars.destroyNonceInv()
		# Encode the long for storage / display to the user
		return CryptoHelper.longEncode(bond)

	@staticmethod
	def genBondFilename():
		"""
		Create a random 16-byte hex string with a .bond extension for storing bonds
		"""
		name = os.urandom(16).encode('hex').upper() + '.bond'
		if Interface.mock:
			name = 'mock-' + name
		return name

	@staticmethod
	def validateBond(bond_str):
		"""
		Bond validation needs to happen server-side, but there's not reason why the
		client can't also verify that they have received a valid bond.
		BOND = m^d, m = OAEP(PREFIX || Hash(k, x) || x).
		"""
		# Make sure the bond holds a number
		try:
			bond = CryptoHelper.longDecode(bond_str)
		except Exception:
			return (False, None, 'Not a valid bond: value encoding')
		# BOND^E = m^d^e = m
		msg = CryptoHelper.longToBytes(CryptoHelper.encrypt(bond))
		# Since OAEP is all-or-nothing, we need to restore the leading zero bytes
		msg = msg.rjust(CryptoVars.OAEP_cipher_len, chr(0))
		# Try to decrypt OAEP format --> (PREFIX || Hash(h, x) || x)
		try:
			msg = CryptoHelper.deOAEP(msg)
		except ValueError:
			return (False, None, 'Not a valid bond: OAEP failure')
		# Check for PREFIX
		if not msg.startswith(CryptoVars.msg_prefix):
			return (False, None, 'Not a valid bond: msg_prefix failure')
		# Extract h = Hash(k, x) and x
		msg = msg[len(CryptoVars.msg_prefix):]
		h = msg[:-CryptoVars.x_len]
		x = msg[-CryptoVars.x_len:]
		# Check for x's prefix
		if not x.startswith(CryptoVars.x_prefix):
			return (False, x, 'Not a valid bond: x_prefix failure')
		# Make sure that the hash is in fact Hash(k, x)
		if h != CryptoHelper.hash(CryptoVars.k, x):
			return (False, x, 'Not a valid bond: hash failure')
		# Huzzah! It's valid!
		return (True, x, 'Success! Valid bond!')

	@staticmethod
	def validateBondFromFile(filename):
		"""
		Given a filename, validate a bond. Useful for client-side verification of
		just-saved bond files.
		"""
		with open(filename, 'r') as f:
			bond = f.read()
		return CryptoClient.validateBond(bond)

class CryptoServer:
	"""
	Provides methods which define actions performed server-side to purchase a
	bitcoin bond.
	FOR SERVER USE ONLY
	"""
	@staticmethod
	def decrypt(s):
		"""
		Wrapper around the decryption method used by Crypto.PublicKey.RSA._RSAobj
		FOR SERVER USE ONLY
		"""
		return CryptoVars.key.decrypt(s)

	@staticmethod
	def genProtobond(token_str):
		"""
		Signs the token to create the protobond.
		PROTOBOND = (m * r^e)^d = (m^d * r^e^d) = (m^d * r) mod n
		FOR SERVER USE ONLY
		"""
		protobond = CryptoServer.decrypt(CryptoHelper.longDecode(token_str))
		return CryptoHelper.longEncode(protobond)

class Interface:
	"""
	Handles the client interface, with all of its bells and whistles.
	Usage: Interface.run(mock=False)
	"""
	# Defines space-based indentation
	padding = 4
	# Terminal width
	width = 80
	# Mock out existence of processing server. Makes use of CryptoServer class.
	mock = None

	@staticmethod
	def run(mock=False):
		"""
		Runs the client interface for bond purchasing.
		"""
		Interface.mock = bool(mock)
		# Clear the screen, print the header
		Interface.clear()
		Interface.header()
		# Connect to server and pull relevant variables
		Interface.waitingFor('Connecting to Dryer 21 server')
		CryptoClient.genCryptoVars()
		Interface.doneWaiting()
		# Generate a token based on those variables
		Interface.waitingFor('Generating token')
		token = CryptoClient.genToken()
		Interface.doneWaiting()
		# Jump to automatic submission
		Interface.autoSubmit(token)

	@staticmethod
	def header():
		"""
		Print the header for the interface, giving the script title and a welcome
		"""
		edge = ' ' * (2 * Interface.padding) + '#' * (Interface.width - 4 * Interface.padding)
		print
		print edge
		print Interface.headerText('DRYER 22 PYTHON SCRIPT')
		print Interface.headerText('A Bitcoin Anonymizer')
		print Interface.headerText('by asuhl, snp, dannybd')
		print edge
		print
		print 'Hello, and welcome to the Dryer 21 Python script!'
		print
		if Interface.mock:
			print 'ENTERING MOCK MODE'
			print

	@staticmethod
	def headerText(text):
		"""
		Center the given text for the header block.
		"""
		s = ' ' * (2 * Interface.padding) + '##'
		s += text.center(max(2, Interface.width - 2 * len(s)))
		s += '##'
		return s

	@staticmethod
	def autoSubmit(token):
		"""
		Automatically submit the generated token. Doing so returns a quote for
		purchasing a bond, so we ping the server on regular intervals to see whether
		the bitcoin transaction for that much on the bond has gone through. Once it
		has, the server will hand us the protobond, and we can continue.
		"""
		print
		print 'Auto-submission selected.'
		print
		# Get the bond quote
		Interface.waitingFor('Sending token to server')
		(price, addr) = DryerServer.fetchQuote(token)
		Interface.doneWaiting()

		print
		print 'Now, please send ' + price + ' to this address: ' + addr
		print
		Interface.horizontalLine()
		print
		# Time to wait between server checks, in seconds
		check_period = 10
		# Ask the server for the protobond
		protobond = DryerServer.fetchProtobond(token)
		while protobond == None:
			Interface.printf('Checking transaction status')
			# Draw dots until time to check again
			for i in range(check_period):
				sleep(1)
				Interface.printf('.')
			# Ask again for the protobond
			protobond = DryerServer.fetchProtobond(token)
			print
		print
		print 'Transaction cleared!'
		print
		Interface.genBond(protobond)

	@staticmethod
	def genBond(protobond):
		"""
		Generate the bond with the received protobond, and save it to a .bond file
		in the current directory.
		"""
		Interface.waitingFor('Generating bond')
		bond = CryptoClient.genBond(protobond)
		Interface.doneWaiting()

		Interface.waitingFor('Validating bond')
		(success, x, msg) = CryptoClient.validateBond(bond)
		if success:
			Interface.doneWaiting()
		else:
			Interface.failWaiting(msg)

		Interface.waitingFor('Saving bond')
		filename = CryptoClient.genBondFilename()
		with open(filename, 'w+') as f:
			f.write(bond)
		Interface.doneWaiting()

		print
		Interface.horizontalLine()
		print
		print 'Congrats! You have successfully purchased a bond. It has been stored here:'
		print
		print os.path.join(os.path.abspath('.'), filename)
		print
		print 'Remember to wait a few days before trying to cash in your bond for 0.1BTC.'
		print 'Thank you for using Dryer 21!'
		print

	@staticmethod
	def printf(stuff):
		"""
		Print to the display without the automatic new line.
		"""
		sys.stdout.write(stuff)
		sys.stdout.flush()

	@staticmethod
	def waitingFor(action):
		"""
		Creates a line like:
		    Beginning foo................................
		With the anticipation of 'DONE' being written at the end.
		"""
		s = ' ' * Interface.padding
		s += action.ljust(Interface.width - 2 * Interface.padding - 4, '.')
		Interface.printf(s)

	@staticmethod
	def doneWaiting():
		"""
		For usage after waitingFor(action).
		"""
		print 'DONE'

	@staticmethod
	def failWaiting(errmsg):
		"""
		For usage after waitingFor(action), in case something goes wrong.
		"""
		print 'FAIL'
		print
		raise NameError('Fail Waiting: ' + errmsg)

	@staticmethod
	def horizontalLine():
		print '=' * Interface.width

	@staticmethod
	def clear():
		print '\n' * 100

	@staticmethod
	def stressTest(trials=100):
		failures = 0
		errors = []
		for i in xrange(trials):
			try:
				Interface.run(mock=True)
			except Exception, e:
				failures += 1
				errors.append((i, str(e)))
		print
		print failures, 'failures out of', trials, 'trials'
		return errors

# Allows for calling from the command line, as in:
# $python dryer21_client.py --auto --mock
if __name__ == '__main__':
	mock = '--mock' in sys.argv[1:]
	Interface.run(mock)