"""
issue_protobond.py:
Carries out the second half of the bond-selling interaction. After a client has already gotten a quote (through gen_quote) and paid to the quoted address, they send their token to issue_protobond. issue_protobond then looks up (with the token) the address in the database, checks that we've been paid, signs the token (turning it into a protobond), updates the database to note that payment was received, and returns the protobond to the client.

Requires:
- Database RPC
- BTC Check RPC
- Sign RPC
"""

from rpc_clients import Database, Check, Sign

import rpc_lib

rpc_lib.set_rpc_socket_path("rpc/IssueProtobond/sock")

@rpc_lib.expose_rpc
def issue_protobond(token):
	"""
	
	"""
	dbentry = Database.get(token=token)
	if dbentry == None:
		raise rpclib.RPCException("No such token in database.")
	address, price = dbentry['address'], dbentry['price']
	if not Check.check(address=address, price=price):
		raise rpclib.RPCException("Payment not received.")
	protobond = Sign.sign(token=token)
	Database.mark_protobond_sent(token=token) # Just a useful flag for database pruning
	return protobond
