"""
gen_quote.py

Exposes a method genquote that does the following:
Given a token, adds (token, index, price, timestamp) to the database and returns (addr, price)

Needs access to:
- Master Public Key
- Database RPC

"""
import random

import bitcoin
import db_client
import global_storage

# Expose only this method to the frontend:
def gen_quote(token, mpk=None):
	"""
	Given a token, adds (token, index, price, timestamp) to the database, and returns (addr, price)

	token is the token, which will identify this transaction in the database.
	mpk is the master public key, from which all the public addresses are derived. It should be gotten from global_storage.get_master_public_key(). If mpk is omitted, gen_quote will call global_storage.get_master_public_key() itself. There is the option to pass mpk in so that it is possible for a long-running process (like gen_quote_server) to avoid calling global_storage.get_master_public_key() every time (as it reads from a file that basically never changes).
	
	index is used with the master public key (mpk) to generate the address.
	"""
	if mpk == None:
		mpk = global_storage.get_master_public_key() # Get master public key if it isn't passed in

	# Index is a large random number that combines with the master public key to yield the address.
	# This combination takes constant time -- it doesn't hurt us to use a very large index.
	# An attacker which knows index, mpk, address, and the _private_ key for address can get the private key for _any_ public key generated using mpk.
	# To limit the damage if one private key gets leaked, we'll make index cryptographically securely random.
	index = random.SystemRandom().getrandbits(128)
	
	address = bitcoin.electrum_address(global_storage.get_master_public_key(), index)

	# Price is the price of a bond, in milliBTC. (We don't use BTC because we don't want floating point errors.)
	price = 100 # 0.1 BTC -- for now, no markup. In the future this may change based on transaction costs, overhead, greediness, etc.

	timestamp = long(time.time())

	
