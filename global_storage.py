import Crypto.Cipher.PKCS1_OAEP as PKCS1_OAEP
import Crypto.Hash.SHA512 as SHA512
import Crypto.PublicKey.RSA as RSA
import base64, functools

bond_price = 14000 # How much we sell bonds for
bond_value = 10000 # How much we redeem bonds for

def memoized(f):
	memo = {}
	@functools.wraps(f)
	def wrapper(*args):
		if args not in memo:
			memo[args] = f(*args)
		return memo[args]
	return wrapper

@memoized
def get_collector_master_public_key():
	public_keystr = open("data/collector_master_public_key/collector_master_public_key.txt").read().strip()
	return public_keystr

@memoized
def get_collector_master_private_key():
	private_keystr = open("data/collector_master_private_key/collector_master_private_key.txt").read().strip()
	return private_keystr

@memoized
def get_dispenser_address():
	address = open("data/dispenser_address/dispenser_address.txt").read().strip()
	return address

@memoized
def get_dispenser_private_key():
	private_keystr = open("data/dispenser_private_key/dispenser_private_key.txt").read().strip()
	return private_keystr

#@memoized
#def get_signing_public_key():
#	public_keystr = open("data/signing_public_key/signing_public_key.txt").read()
#	return importKey(public_keystr)

@memoized
def get_signing_private_key():
	private_keystr = open("data/signing_private_key/signing_private_key.txt").read()
	return importKey(private_keystr)

@memoized
def get_mixin_address():
	address = open("data/mixin_address/mixin_address.txt").read().strip()
	return address

def importKey(keystr):
	"""
	From a base64-encoded string defining an RSA key, create the key and its n.
	"""
	return RSA.importKey(base64.b64decode(keystr))

class CryptoVars:
	"""
	Stores the variables involved within the crypto processes.
	"""
	# key, n correspond to the 4096-bit RSA used in the token and bond
	keystr = 'MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEApYV26Umk/uU0Gau29/XNKhxtA1P6fwhMctW+5Jqg32tYwVk2ZUMGHzgDexZdHmOoHYFYllP1TuWZEMpTwxMCJtV0gWhBGdUmAECVnVwmzfG2RvCfVSlmbNei2C6I2mlC05eg0tXyGW4AGXG8yfhW/P2mD23B7zZGzY8/thCWCYGnbNG9i0+Qk4muohLyoLhIGcHK38yDmsjQ3JFSSwrg2S6iXa/dfXbPonNZZvSZAUYBeRaZoJYtmD8hygQSy++HQ254las1UtTLlvdLZ9O6vIg6y0vCSjWn1NCqAYlm94mFxk9cIB9iIkmES37sLZMG8YD47xCxiLAcIxpwoVJJVrIc+wQoT4qNSdCixQG0Z7HA7+DcWA1txFSH8zaTmCI0AKL5zxSsitzprB8TJcaDAFq7DXUW1LuysnEEdm+Nf20MLZ/pwjJu4lMkP0K/ukdt0VHXSjNYZkhUEwUju3T0W10ZzdCjL3AdjnPBw/CMaCOaXxjsN/9qhH59p8+FmFUu749mp6j+5u25o93SEnPy8xDbf6wNjueU2a4z10u4o16frfIEwz84peGKeamGH9ALLV3nlC+bVd7AhE3MfXQ/B1YJUxPVhmYkKJvkRcBTpZMIGhzVG5PwTLxS1GDz0mhoBkic8RDVN6fVpkEutA9nZGgKFBL+u+rPa5JjSLwP3mcCAwEAAQ=='
	key = importKey(keystr)
	n = key.n
	# OAEP_cipher is also based on 4096-bit RSA, and contains both the public
	# and private key. This is NOT used for encrypting the token or bond, but
	# instead to encrypt and descrypt the message [OAEP(Hash(n, x) || x)].
	# We're using PyCrypto for our encryption, and it only provides OAEP as part
	# of PKCS1_OAEP, which requires an encryption scheme. By providing the private
	# key of the OAEP_cipher publicly, we annul the encryption part of the cipher
	# but maintain OAEP's all-or-nothing attribute.
	OAEP_keystr = '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'
	OAEP_key = importKey(OAEP_keystr)
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
