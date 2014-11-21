"""
gen_quote.py

Exposes a method genquote that does the following:
Given a token, adds (token, index, price, timestamp) to the database and returns (addr, price)

Needs access to:
- Master Public Key
- Database RPC

"""

import bitcoin
import db_client

# Expose only this method to the frontend:
def gen_quote(token):
	"""
	Given a token, adds (token, index, price, timestamp) to the database, and returns (addr, price)
	index is used with the master public key to generate the address.
	"""
	pass
