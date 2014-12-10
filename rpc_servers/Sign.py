"""
Sign.py:
Signs tokens, making them protobonds
It is vital to the security of our system that Sign.sign be deterministic.
"""

import base64
import global_storage
import rpc_lib

rpc_lib.set_rpc_socket_path("rpc/Sign/sock")

@rpc_lib.expose_rpc
def sign(token_str):
	"""
	Signs the token to create the protobond.
	PROTOBOND = (m * r^e)^d = (m^d * r^e^d) = (m^d * r) mod n
	"""
	key = global_storage.get_crypto_private_key()
	protobond = key.decrypt(longDecode(token_str))
	return longEncode(protobond)

def longEncode(n):
	"""
	Encodes a long in a base64 string which is easily sendable / storable
	"""
	return base64.b64encode(hex(n))

def longDecode(s):
	"""
	Decodes a base64 string (formed by longEncode) into a long
	"""
	return long(base64.b64decode(s), 16)
