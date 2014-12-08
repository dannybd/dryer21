from base64 import b64encode, b64decode
import Crypto.Util.number as CryptoNumber
import Crypto.Cipher.PKCS1_OAEP as PKCS1_OAEP
import Crypto.Hash.SHA512 as SHA512
import Crypto.PublicKey.RSA as RSA
import json
import os
import sys
from time import sleep, time
from urllib import urlencode

class DryerServer:
	"""
	Handles connections to the server, and interpretations of the responses.
	"""
	BASE_URL = 'http://asym3f2krhdh7mzx.onion/'
	MOCK_BASE_URL = 'http://dannybd.mit.edu/6.858/'
	CONNECT_URL = 'connect'
	QUOTE_URL = 'quote'
	PROTOBOND_URL = 'protobond'
	LEGAL_URLS = [CONNECT_URL, QUOTE_URL, PROTOBOND_URL]

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
			if Interface.mock:
				import urllib2
				response = urllib2.urlopen(DryerServer.MOCK_BASE_URL + url, urlencode(data))
			else:
				import torsocket
				response = torsocket.urlopen(DryerServer.BASE_URL + url, urlencode(data))
		except Exception:
			Interface.failWaiting(errmsg)
		try:
			return json.load(response)
		except ValueError:
			Interface.failWaiting('JSON error in returned data.')

	@staticmethod
	def fetchConnect():
		"""
		Initial connectivity test to the server.
		"""
		data = DryerServer.load(
			url=DryerServer.CONNECT_URL,
			data={'mock': Interface.mock},
		)
		if Interface.mock:
			CryptoVars.keystr = data['private_key']
			CryptoVars.key = CryptoHelper.importKey(CryptoVars.keystr)
			CryptoVars.n = CryptoVars.key.n
		return bool(data['success'])

	@staticmethod
	def fetchQuote(token):
		"""
		Sending up a token returns a quote to the user, containing the current cost
		of a bond (fluctating with transaction feeds) and a Bitcoin address where
		the user should send their Bitcoin.
		"""
		data = DryerServer.load(
			url=DryerServer.QUOTE_URL,
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
			url=DryerServer.PROTOBOND_URL,
			data={'token': token},
			errmsg='Unable to check server for protobond. Please connect and try again.',
		)
		protobond = data.get('protobond', None)
		if protobond and Interface.mock:
			protobond = CryptoServer.genProtobond(token)
		return protobond

class CryptoHelper:
	"""
	A class of helper methods for making the crypto work.
	"""
	@staticmethod
	def importKey(keystr):
		"""
		From a base64-encoded string defining an RSA key, create the key and its n.
		"""
		return RSA.importKey(b64decode(keystr))

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

class CryptoVars:
	"""
	Stores the variables involved within the crypto processes.
	"""
	# key, n correspond to the 4096-bit RSA used in the token and bond
	keystr = 'MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEApYV26Umk/uU0Gau29/XNKhxtA1P6fwhMctW+5Jqg32tYwVk2ZUMGHzgDexZdHmOoHYFYllP1TuWZEMpTwxMCJtV0gWhBGdUmAECVnVwmzfG2RvCfVSlmbNei2C6I2mlC05eg0tXyGW4AGXG8yfhW/P2mD23B7zZGzY8/thCWCYGnbNG9i0+Qk4muohLyoLhIGcHK38yDmsjQ3JFSSwrg2S6iXa/dfXbPonNZZvSZAUYBeRaZoJYtmD8hygQSy++HQ254las1UtTLlvdLZ9O6vIg6y0vCSjWn1NCqAYlm94mFxk9cIB9iIkmES37sLZMG8YD47xCxiLAcIxpwoVJJVrIc+wQoT4qNSdCixQG0Z7HA7+DcWA1txFSH8zaTmCI0AKL5zxSsitzprB8TJcaDAFq7DXUW1LuysnEEdm+Nf20MLZ/pwjJu4lMkP0K/ukdt0VHXSjNYZkhUEwUju3T0W10ZzdCjL3AdjnPBw/CMaCOaXxjsN/9qhH59p8+FmFUu749mp6j+5u25o93SEnPy8xDbf6wNjueU2a4z10u4o16frfIEwz84peGKeamGH9ALLV3nlC+bVd7AhE3MfXQ/B1YJUxPVhmYkKJvkRcBTpZMIGhzVG5PwTLxS1GDz0mhoBkic8RDVN6fVpkEutA9nZGgKFBL+u+rPa5JjSLwP3mcCAwEAAQ=='
	key = CryptoHelper.importKey(keystr)
	n = key.n
	# OAEP_cipher is also based on 4096-bit RSA, and contains both the public
	# and private key. This is NOT used for encrypting the token or bond, but
	# instead to encrypt and descrypt the message [OAEP(Hash(n, x) || x)].
	# We're using PyCrypto for our encryption, and it only provides OAEP as part
	# of PKCS1_OAEP, which requires an encryption scheme. By providing the private
	# key of the OAEP_cipher publicly, we annul the encryption part of the cipher
	# but maintain OAEP's all-or-nothing attribute.
	OAEP_keystr = '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'
	OAEP_key = CryptoHelper.importKey(OAEP_keystr)
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
	# Holds the inverse of the nonce, for generating the bond from the protobond.
	# Needs to be destroyed after use, so we're storing it as a value here and not
	# passing it as an argument between frames to minimize copies in memory.
	nonce_inv = None

class CryptoClient:
	"""
	Provides methods which define actions performed client-side to purchase a
	bitcoin bond.
	"""
	@staticmethod
	def connect():
		"""
		Connects to server
		"""
		DryerServer.fetchConnect()

	@staticmethod
	def genToken():
		"""
		Generates a token, which is of the form (m*r^e) mod n.
		Contains a message, m, which is of the form OAEP(PREFIX || Hash(n, x) || x),
		as well as a nonce, r, which is encrypted. The nonce's inverse is generated
		and stored for final bond generation later.
		"""
		# Generate x, which is random with a prefix for verification purposes
		x = CryptoVars.x_prefix + os.urandom(CryptoVars.x_entropy_bytes)
		# h = Hash(n, x)
		h = CryptoHelper.hash(CryptoHelper.longToBytes(CryptoVars.n), x)
		# m = OAEP(PREFIX || Hash(n, x) || x)
		m = CryptoHelper.OAEP(CryptoVars.msg_prefix + h + x)
		# Convert to a long mod n
		m = CryptoHelper.bytesToLong(m)
		if m != (m % CryptoVars.n):
			raise ValueError('OAEP_cipher._key.n > key.n causing invalid m')
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
		del CryptoVars.nonce_inv
		# Encode the long for storage / display to the user
		return CryptoHelper.longEncode(bond)

	@staticmethod
	def saveBondToFile(bond):
		"""
		Create a random 16-byte hex filename with a .bond extension, store the
		bond there, and return the filename.
		"""
		filename = os.urandom(16).encode('hex').upper() + '.bond'
		if Interface.mock:
			filename = 'mock-' + filename
		try:
			with open(filename, 'w+') as f:
				f.write(bond)
		except Exception:
			raise NameError('Failed to save bond to file!')
		return filename

	@staticmethod
	def validateBond(bond_str):
		"""
		Bond validation needs to happen server-side, but there's not reason why the
		client can't also verify that they have received a valid bond.
 		BOND = m^d, m = OAEP(PREFIX || Hash(n, x) || x).
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
		# Extract h = Hash(n, x) and x
		msg = msg[len(CryptoVars.msg_prefix):]
		h = msg[:-CryptoVars.x_len]
		x = msg[-CryptoVars.x_len:]
		# Check for x's prefix
		if not x.startswith(CryptoVars.x_prefix):
			return (False, x, 'Not a valid bond: x_prefix failure')
		# Make sure that the hash is in fact Hash(n, x)
		if h != CryptoHelper.hash(CryptoHelper.longToBytes(CryptoVars.n), x):
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
	# Toggle actually saving bonds into files
	save = None
	# Mock out existence of processing server. Makes use of CryptoServer class.
	mock = None

	@staticmethod
	def run(save=True, mock=False):
		"""
		Runs the client interface for bond purchasing.
		"""
		Interface.save = bool(save)
		Interface.mock = bool(mock)
		# Clear the screen, print the header
		Interface.clear()
		Interface.header()
		# Connect to server and pull relevant variables
		Interface.waitingFor('Connecting to Dryer 21 server')
		CryptoClient.connect()
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
		print Interface.headerText('DRYER 21 PYTHON SCRIPT')
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

		if Interface.save:
			Interface.waitingFor('Saving bond')
			filename = CryptoClient.saveBondToFile(bond)
			Interface.doneWaiting()

			print
			Interface.horizontalLine()
			print
			print 'Congrats! You have successfully purchased a bond. It has been stored here:'
			print
			print os.path.join(os.path.abspath('.'), filename)
		else:
			print
			Interface.horizontalLine()
			print
			print 'Congrats! You have successfully purchased a bond. Here it is:'
			print
			print bond
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

	testTrials = None
	testTrialNum = None
	testFailures = None
	testErrors = None
	testStart = None
	testEnd = None
	testDuration = None

	@staticmethod
	def stressTest(trials=100):
		Interface.testTrials = trials
		Interface.testFailures = 0
		Interface.testErrors = []
		Interface.testStart = time()
		try:
			for i in xrange(trials):
				Interface.testTrialNum = i
				try:
					Interface.run(save=False, mock=True)
				except Exception, e:
					Interface.testFailures += 1
					Interface.testErrors.append((i, str(e)))
		except KeyboardInterrupt:
			trials = i + 1
		finally:
			Interface.testEnd = time()
			Interface.testDuration = Interface.testEnd - Interface.testStart
			print
			print
			Interface.horizontalLine()
			Interface.horizontalLine()
			print
			print Interface.testFailures, 'failures out of', trials, 'trials'
			print 'Ran for %.3f seconds' % (Interface.testDuration)
			print 'Errors:', Interface.testErrors

# Allows for calling from the command line, as in:
# $python dryer21_client.py --mock --nosave
if __name__ == '__main__':
	save = not ('--nosave' in sys.argv[1:])
	mock = '--mock' in sys.argv[1:]
	Interface.run(save=save, mock=mock)
