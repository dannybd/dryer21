"""
Verify.py:
Validates bonds to determine if they're kosher
"""

from base64 import b64encode, b64decode
import Crypto.Util.number as CryptoNumber
import Crypto.Hash.SHA512 as SHA512
from global_storage import CryptoVars
import rpc_lib

rpc_lib.set_rpc_socket_path("rpc/Verify/sock")

@rpc_lib.expose_rpc
def verify(bond_str):
	"""
	Verify that we have received a valid bond.
	BOND = m^d, m = OAEP(PREFIX || Hash(n, x) || x).
	"""
	# Make sure the bond holds a number
	try:
		bond = longDecode(bond_str)
	except Exception:
		print 'Not a valid bond: value encoding'
		return False
	# BOND^e = m^d^e = m
	msg = longToBytes(encrypt(bond))
	# Since OAEP is all-or-nothing, we need to restore the leading zero bytes
	msg = msg.rjust(CryptoVars.OAEP_cipher_len, chr(0))
	# Try to decrypt OAEP format --> (PREFIX || Hash(h, x) || x)
	try:
		msg = deOAEP(msg)
	except ValueError:
		print 'Not a valid bond: OAEP failure'
		return False
	# Check for PREFIX
	if not msg.startswith(CryptoVars.msg_prefix):
		print 'Not a valid bond: msg_prefix failure'
		return False
	# Extract h = Hash(n, x) and x
	msg = msg[len(CryptoVars.msg_prefix):]
	h = msg[:-CryptoVars.x_len]
	x = msg[-CryptoVars.x_len:]
	# Check for x's prefix
	if not x.startswith(CryptoVars.x_prefix):
		print 'Not a valid bond: x_prefix failure'
		return False
	# Make sure that the hash is in fact Hash(n, x)
	if h != hash(longToBytes(CryptoVars.n), x):
		print 'Not a valid bond: hash failure'
		return False
	# Huzzah! It's valid!
	print 'Success! Valid bond!'
	return True

def longDecode(s):
	"""
	Decodes a base64 string (formed by longEncode) into a long
	"""
	return long(b64decode(s), 16)

def encrypt(s):
	"""
	Wrapper around the encryption method used by Crypto.PublicKey.RSA._RSAobj
	"""
	# (the second argument is ignored, according to PyCrypto docs)
	return CryptoVars.key.encrypt(s, 0)[0]

def longToBytes(n):
	"""
	Wrapper around the long-->bytestring method in Crypto.Util.number
	"""
	return CryptoNumber.long_to_bytes(n)

def deOAEP(s):
	"""
	Decrypt a string using OAEP and the OAEP cipher stored above. Note that this
	does NOT use the main RSA encryption used for token and bond generation.
	"""
	return CryptoVars.OAEP_cipher.decrypt(s)

def hash(*args):
	"""
	Update a new SHA512 hash with one argument at a time, and return that hash.
	"""
	h = SHA512.new()
	for arg in args:
		h.update(arg)
	return h.digest()
