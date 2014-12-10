"""
gen_quote.py

Exposes a method genquote that does the following:
Given a token, adds (token, index, price, timestamp) to the database and returns (addr, price)

Needs access to:
- Master Bitcoin Public Key (for deterministic wallet generation)
- Database RPC

"""
import random

import bitcoin
from rpc_clients import Database
import global_storage

import rpc_lib

rpc_lib.set_rpc_socket_path("rpc/GenQuote/sock")

@rpc_lib.expose_rpc
def gen_quote(token):
	"""
	Given a token, adds (token, index, price, timestamp) to the database, and returns (addr, price)
	If token already exists in the database, return the already-existing (addr, price).

	token is the token, which will identify this transaction in the database.
	mpk is the master public key, from which all the public addresses are derived. It should be gotten from global_storage.get_master_public_key().
	
	index is used with the master public key (mpk) to generate the address.

	price is in satoshi.
	"""
	mpk = global_storage.get_master_public_key()

	if not sanetoken(token):
		raise rpclib.RPCException("Token not sane.")

	# FIXME: Should we be worried about race conditions here?
	dbentry = Database.get(token=token)
	if dbentry != None: # This token is already in the database.
		index, address, price = dbentry['index'], dbentry['address'], dbentry['price']
		assert address == bitcoin.electrum_address(mpk, index) # Index is the index used to generate address.(deterministic key generation)
	else:
		# Index is a large random number that combines with the master public key to yield the address. This combination takes constant time -- it doesn't hurt us to use a very large index. An attacker which knows index, mpk, address, and the _private_ key for address can get the private key for _any_ public key generated using mpk. To limit the damage if one private key gets leaked, we'll make index cryptographically securely random, even though it's probably unnecessary.
		index = random.SystemRandom().getrandbits(128)
		address = bitcoin.electrum_address(mpk, index)
		# Price is the price to buy a bond, in satoshi. (We don't use BTC because we don't want floating point errors.)
		price = 10 ** 7 # 0.1 BTC -- for now, no markup. In the future this may change based on transaction costs, overhead, greediness, etc.
		Database.put(token=token, index=index, address=address, price=price)
	return (address, price)

def sanetoken(token):
	"""
	Internal method to be sure people aren't sending us 15 MB GIFs as tokens.
	"""
	# len(CryptoHelper.longEncode(2**4096)) = 1372
	MAX_TOKEN_LEN = 1372
	return len(token) <= MAX_TOKEN_LEN
