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
	BASE_URL = 'http://dannybd.mit.edu/6.858/'
	INIT_URL = 'fetch_crypto_vars.php'
	TOKEN_URL = 'fetch_quote.php'
	PROTOBOND_URL = 'fetch_protobond.php'
	LEGAL_URLS = [INIT_URL, TOKEN_URL, PROTOBOND_URL]

	errmsg = 'Unable to connect to server. Please connect and try again.'

	@staticmethod
	def load(url, data={}, errmsg=errmsg):
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
		data = DryerServer.load(DryerServer.INIT_URL)
		(key, n, e) = CryptoHelper.importKey(data['key'])
		return (key, n, e, data['k0'], data['k1'])

	@staticmethod
	def fetchQuote(token):
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
		if Interface.mock:
			return CryptoServer.genProtobond(token)
		data = DryerServer.load(
			DryerServer.PROTOBOND_URL,
			data={'token': token},
			errmsg='Unable to check server for protobond. Please connect and try again.',
		)
		return data.get('protobond', None)

class CryptoVars:
	key = None
	n = None
	e = None
	k0 = None
	k1 = None

	x_tag = '[[6.858]]'
	x_entropy_bytes = 256
	x_len = x_entropy_bytes + len(x_tag)

	nonce_inv = None

	@staticmethod
	def init(key, n, e, k0, k1):
		CryptoVars.key = key
		CryptoVars.n = n
		CryptoVars.e = e
		CryptoVars.k0 = k0
		CryptoVars.k1 = k1

	@staticmethod
	def destroyNonceInv():
		CryptoVars.nonce_inv = int(os.urandom(256).encode('hex'), 16)
		del CryptoVars.nonce_inv

class CryptoHelper:
	OAEP_cipher = None

	@staticmethod
	def importKey(keystr):
		key = RSA.importKey(b64decode(keystr))
		return (key, key.n, key.e)

	@staticmethod
	def hash(*args):
		h = SHA512.new()
		for arg in args:
			h.update(arg)
		return h.digest()

	@staticmethod
	def genOAEPCipher():
		if CryptoHelper.OAEP_cipher == None:
			CryptoHelper.OAEP_cipher = PKCS1_OAEP.new(CryptoVars.key, SHA512)
		return CryptoHelper.OAEP_cipher

	@staticmethod
	def OAEP(*args):
		cipher = CryptoHelper.genOAEPCipher()
		# NOTE (dannybd): OAEP can only encrypt 382 bytes of input
		#	with a 4096-bit RSA key. FIX THIS.
		return cipher.encrypt(''.join(args))

	@staticmethod
	def genNonce():
		nonce = CryptoNumber.getRandomRange(0, CryptoVars.n)
		CryptoVars.nonce_inv = CryptoNumber.inverse(nonce, CryptoVars.n)
		return CryptoHelper.encrypt(nonce)

	@staticmethod
	def encrypt(s):
		return CryptoVars.key.encrypt(s, os.urandom(64))[0]

	@staticmethod
	def bytesToLong(s):
		return CryptoNumber.bytes_to_long(s)

	@staticmethod
	def longToBytes(n):
		return CryptoNumber.long_to_bytes(n)

	@staticmethod
	def longEncode(n):
		return b64encode(hex(n))

	@staticmethod
	def longDecode(s):
		return long(b64decode(s), 16)

	# FOR SERVER ONLY
	@staticmethod
	def decrypt(s):
		return CryptoVars.key.decrypt(s)

	# FOR SERVER ONLY
	@staticmethod
	def deOAEP(s):
		cipher = CryptoHelper.genOAEPCipher()
		msg = cipher.decrypt(s)
		h = msg[:-CryptoVars.x_len]
		x = msg[-CryptoVars.x_len:]
		return (h, x)

class CryptoClient:
	@staticmethod
	def genCryptoVars():
		CryptoVars.init(*DryerServer.fetchCryptoVars())

	@staticmethod
	def genToken():
		x = CryptoVars.x_tag + os.urandom(CryptoVars.x_entropy_bytes)
		h0 = CryptoHelper.hash(CryptoVars.k0, x)
		# h1 = CryptoHelper.hash(CryptoVars.k1, x)
		m = CryptoHelper.OAEP(h0, x)
		m = CryptoHelper.bytesToLong(m) % CryptoVars.n
		nonce_e = CryptoHelper.genNonce()
		nonce_e = nonce_e % CryptoVars.n
		token = (m * nonce_e) % CryptoVars.n
		return CryptoHelper.longEncode(token)

	@staticmethod
	def genBond(protobond_str):
		protobond = CryptoHelper.longDecode(protobond_str)
		bond = (protobond * CryptoVars.nonce_inv) % CryptoVars.n
		CryptoVars.destroyNonceInv()
		return CryptoHelper.longEncode(bond)

	@staticmethod
	def genBondFilename():
		#use CryptoVars.nonce_int to decrypt protobond --> bond
		return os.urandom(16).encode('hex').upper() + '.bond'

# FOR SERVER ONLY
class CryptoServer:
	@staticmethod
	def genProtobond(token_str):
		protobond = CryptoHelper.decrypt(CryptoHelper.longDecode(token_str))
		return CryptoHelper.longEncode(protobond)

	@staticmethod
	def validateBond(bond_str):
		try:
			bond = CryptoHelper.longDecode(bond_str)
		except Exception:
			return (False, None, 'Not a valid bond: value encoding')
			return failure
		bond_e = CryptoHelper.longToBytes(CryptoHelper.encrypt(bond))
		try:
			(h, x) = CryptoHelper.deOAEP(bond_e)
		except ValueError:
			return (False, None, 'Not a valid bond: OAEP failure')
		if not x.startswith(CryptoVars.x_tag):
			return (False, x, 'Not a valid bond: x_tag failure')
		if h == CryptoHelper.hash(CryptoVars.k0, x):
			return (True, x, 'Success! Valid bond!')
		return (False, x, 'Not a vaqlid bond: hash failure')

	@staticmethod
	def validateBondFromFile(filename):
		with open(filename, 'r') as f:
			bond = f.read()
		return CryptoServer.validateBond(bond)

class Interface:
	padding = 4
	width = 80
	auto = None
	mock = None
	sysExit = (__name__ == '__main__')

	@staticmethod
	def printf(stuff):
		sys.stdout.write(stuff)
		sys.stdout.flush()

	@staticmethod
	def waitingFor(action):
		s = ' ' * Interface.padding
		s += action
		num_dots = max(
			0,
			Interface.width - 2 * Interface.padding - len(action) - len('DONE'),
		)
		s += '.' * num_dots
		Interface.printf(s)

	@staticmethod
	def doneWaiting():
		print 'DONE'

	@staticmethod
	def failWaiting(errmsg):
		print 'FAIL'
		print
		print errmsg
		print
		if Interface.sysExit:
			sys.exit(2)
		else:
			raise NameError('System would normally exit here with error 2')

	@staticmethod
	def horizontalLine():
		print '=' * Interface.width

	@staticmethod
	def clear():
		print '\n' * 100

	@staticmethod
	def run(auto=False, mock=False):
		Interface.auto = bool(auto)
		Interface.mock = bool(mock)

		Interface.clear()
		Interface.header()

		Interface.waitingFor('Connecting to Dryer 21 server')
		CryptoClient.genCryptoVars()
		Interface.doneWaiting()

		Interface.waitingFor('Generating token')
		token = CryptoClient.genToken()
		Interface.doneWaiting()

		if Interface.auto:
			Interface.autoSubmit(token)
		else:
			Interface.tokenInstructions(token)

		if Interface.sysExit:
			sys.exit(0)

	@staticmethod
	def header():
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
		s = ' ' * (2 * Interface.padding) + '##'
		total_spaces = max(2, Interface.width - 2 * len(s) - len(text))
		left_spaces = total_spaces / 2
		right_spaces = total_spaces - left_spaces
		s += ' ' * left_spaces
		s += text
		s += ' ' * right_spaces + '##'
		return s

	@staticmethod
	def tokenInstructions(token):
		print
		print 'Please copy the following token into your browser:'
		print
		print token
		print
		Interface.horizontalLine()
		print
		print 'Type \'c\' to continue, or \'p\' to submit via Python.'
		user_input = raw_input('(c or p, then Enter) > ')
		while len(user_input) < 1 or user_input[0] not in 'cp':
			print
			print 'Sorry, that is not a valid entry.'
			print 'Type \'c\' to continue, or \'p\' to submit via Python.'
			user_input = raw_input('(c or p, then Enter) > ')
		print
		if user_input == 'c':
			Interface.waitForProtobond()
		elif user_input == 'p':
			Interface.autoSubmit(token)

	@staticmethod
	def waitForProtobond():
		print 'Paste the text from Step 4 below, and press Enter:'
		print
		protobond = raw_input()
		print
		Interface.horizontalLine()
		print
		Interface.genBond(protobond)

	@staticmethod
	def autoSubmit(token):
		print
		print 'Auto-submission selected.'
		print

		Interface.waitingFor('Sending token to server')
		(price, addr) = DryerServer.fetchQuote(token)
		Interface.doneWaiting()

		print
		print 'Now, please send ' + price + ' to this address: ' + addr
		print
		Interface.horizontalLine()
		print

		check_period = 10
		protobond = DryerServer.fetchProtobond(token)
		while protobond == None:
			Interface.printf('Checking transaction status')
			for i in range(check_period):
				sleep(1)
				Interface.printf('.')
			protobond = DryerServer.fetchProtobond(token)
			print
		print
		print 'Transaction cleared!'
		print
		Interface.genBond(protobond)

	@staticmethod
	def genBond(protobond):
		Interface.waitingFor('Generating bond')
		bond = CryptoClient.genBond(protobond)
		Interface.doneWaiting()

		Interface.waitingFor('Saving bond')
		filename = CryptoClient.genBondFilename()
		with open(filename, 'w+') as f:
			f.write(bond)
		Interface.doneWaiting()

		print
		Interface.horizontalLine()
		print
		print 'Congrats! You have successfully generated a bond. It has been stored here:'
		print
		print os.path.join(os.path.abspath('.'), filename)
		print
		print 'Remember to wait a few days before trying to cash in your bond for 0.1BTC.'
		print 'Thank you for using Dryer 21!'
		print
		if Interface.mock:
			print 'MOCK MODE ONLY: VALIDATION'
			Interface.waitingFor('Validating bond')
			(success, x, msg) = CryptoServer.validateBond(bond)
			if success:
				Interface.doneWaiting()
				print 'Congrats! x even begins with "' + CryptoVars.x_tag + '"!'
				print
			elif x:
				Interface.failWaiting('At least you got x:' + x.decode('utf-8', 'ignore'))
			else:
				Interface.failWaiting('So sad')
			print msg
			print

if __name__ == '__main__':
	auto = '--auto' in sys.argv[1:]
	mock = '--mock' in sys.argv[1:]
	Interface.run(auto, mock)