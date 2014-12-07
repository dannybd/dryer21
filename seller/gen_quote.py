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
import db_rpcclient
import global_storage

@expose_rpc
def gen_quote(token, mpk=None):
	"""
	Given a token, adds (token, index, price, timestamp) to the database, and returns (addr, price)
	If token already exists in the database, return the already-existing (addr, price).

	token is the token, which will identify this transaction in the database.
	mpk is the master public key, from which all the public addresses are derived. It should be gotten from global_storage.get_master_public_key(). If mpk is omitted, gen_quote will call global_storage.get_master_public_key() itself. There is the option to pass mpk in so that it is possible for a long-running process (like gen_quote_server) to avoid calling global_storage.get_master_public_key() every time (as it reads from a file that basically never changes).
	
	index is used with the master public key (mpk) to generate the address.

	price is in satoshi.
	"""
	if mpk == None:
		mpk = global_storage.get_master_public_key() # Get master public key if it isn't passed in

	assert mpk != None

	# FIXME Should we be worried about race conditions here?
	dbentry = db_rpcclient.get(token)
	if dbentry != None: # This token is already in the database.
		index, address, price = dbentry['index'], dbentry['address'], dbentry['price']
		assert address == bitcoin.electrum_address(mpk, index) # Index is the index used to generate address.
		return (address, price)
	else:
		# Index is a large random number that combines with the master public key to yield the address. This combination takes constant time -- it doesn't hurt us to use a very large index. An attacker which knows index, mpk, address, and the _private_ key for address can get the private key for _any_ public key generated using mpk. To limit the damage if one private key gets leaked, we'll make index cryptographically securely random, even though it's probably unnecessary.
		index = random.SystemRandom().getrandbits(128)
		address = bitcoin.electrum_address(mpk, index)
		# Price is the price to buy a bond, in satoshi. (We don't use BTC because we don't want floating point errors.)
		price = 10 ** 7 # 0.1 BTC -- for now, no markup. In the future this may change based on transaction costs, overhead, greediness, etc.
		timestamp = long(time.time())
		db_rpcclient.put(token=token, index=index, address=address, price=price, timestamp=timestamp)
		return (address, price)
