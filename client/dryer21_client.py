import urllib, urllib2
import json, base64
import os, time
import sys

class DryerServer:
	BASE_URL = 'http://dannybd.mit.edu/6.858/'
	INIT_URL = 'get_crypto_vars.php'
	TOKEN_URL = 'send_token.php'
	PROTOBOND_URL = 'gen_bond.php'
	LEGAL_URLS = [INIT_URL, TOKEN_URL, PROTOBOND_URL]

	errmsg = 'Unable to connect to server. Please connect and try again.'

	@staticmethod
	def load(url, data={}, errmsg=errmsg):
		if url not in DryerServer.LEGAL_URLS:
			raise ValueError('Need to use a valid URL')
		try:
			data = urllib.urlencode(data)
			response = urllib2.urlopen(DryerServer.BASE_URL + url, data)
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
		data = DryerServer.load(
			DryerServer.PROTOBOND_URL,
			data={'token': token},
			errmsg='Unable to check server for bond. Please connect and try again.',
		)
		if 'bond' in data:
			return data['bond']
		return None

class CryptoVars:
	key = None
	n = None
	e = None
	k0 = None
	k1 = None

	token = None
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
	'''These all need to be fleshed out.'''

	@staticmethod
	def importKey(keystr):
		"""
		key = RSA.importKey(keystr)
		return (key, key.n, key.e)
		"""
		key = keystr
		n = 19265913675216539088843522501252411662825554850796361827227960156161459812318843097684892671824121383601843001515365764542823434062081610090132286593406741078753926537029367904115073634501913394860880829521050873958277983601458665370820723093698021978943905525455260342305112938652009878186489754492929483584194773388463861993225718025085771559343862752795962454563335571465911419218104988342046035221946848331410247421318706697432265231985297965243678514004991110370711468048275031256214816393667064866273111535752732021320957901948229007977761275028310027981536615677558234513453776239448487089967455559204268595079L
		e = 65537L
		return (key, n, e)

	@staticmethod
	def hash(x, k):
		'''
		h = SHA512.new()
		h.update(k)
		h.update(x)
		return h.digest()
		'''
		return k + x

	@staticmethod
	def OAEP(s0, s1):
		'''
		???
		'''
		return s0 + s1

	@staticmethod
	def genNonce():
		'''
		r = Util.number.getRandomRange(0, CryptoVars.n)
		CryptoVars.nonce_inv = Util.number.inverse(r, CryptoVars.n)
		return CryptoHelper.encrypt(r)
		'''
		r = CryptoHelper.bytesToLong(os.urandom(256)) % CryptoVars.n
		print '~~~', 'r', r, '~~~'
		return CryptoHelper.encrypt(r)

	@staticmethod
	def genToken():
		x = 'dannybd' # base64.b64encode(os.urandom(256))
		h0 = CryptoHelper.hash(CryptoVars.k0, x)
		h1 = CryptoHelper.hash(CryptoVars.k1, x)
		m = CryptoHelper.OAEP(h0, h1 + x)
		m = CryptoHelper.bytesToLong(m) % CryptoVars.n
		r_e = CryptoHelper.genNonce()
		token = (m * r_e) % CryptoVars.n
		return CryptoHelper.longEncode(token)

	@staticmethod
	def genBond(protobond):
		#use CryptoVars.nonce_int to decrypt protobond --> bond
		CryptoVars.destroyNonceInv()
		return protobond[::-1]

	@staticmethod
	def genBondFilename():
		#use CryptoVars.nonce_int to decrypt protobond --> bond
		return base64.b16encode(os.urandom(16)) + '.bond'

	@staticmethod
	def encrypt(s):
		return s

	@staticmethod
	def bytesToLong(s):
		'''
		return Util.number.bytes_to_long(s)
		'''
		return int(s.encode('hex'), 16)

	@staticmethod
	def longEncode(n):
		return base64.b64encode(hex(n))

	@staticmethod
	def longDecode(s):
		return long(base64.b64decode(s), 16)

class Interface:
	padding = 4
	width = 80

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
		sys.exit(2)

	@staticmethod
	def horizontalLine():
		print '=' * Interface.width

	@staticmethod
	def clear():
		print '\n' * 100

	@staticmethod
	def run():
		Interface.clear()
		Interface.header()

		Interface.waitingFor('Connecting to Dryer 21 server')
		CryptoVars.init(*DryerServer.fetchCryptoVars())
		Interface.doneWaiting()

		Interface.waitingFor('Generating token')
		token = CryptoHelper.genToken()
		Interface.doneWaiting()

		Interface.tokenInstructions(token)
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
				time.sleep(1)
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
		bond = CryptoHelper.genBond(protobond)
		Interface.doneWaiting()

		Interface.waitingFor('Saving bond')
		filename = CryptoHelper.genBondFilename()
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

if __name__ == '__main__':
	Interface.run()