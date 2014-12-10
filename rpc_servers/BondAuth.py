"""
BondAuth:

Requires:
- Verify RPC (to verify the bonds)
- BlacklistDB RPC (to add bonds to the blacklist)
"""

import rpc_lib

from rpc_clients import Verify, BlacklistDB

rpc_lib.set_rpc_socket_path("rpc/BondAuth/sock")

@rpc_lib.expose_rpc
def bond_auth(bond, address):
	"""
	Given a bond and an address, verifies the bond and then adds the bond and address to the BlacklistDB for later redemption.
	Returns True on success, raises exception on error.
	"""
	if not valid_address(address):
		raise rpc_lib.RPCException("Invalid address.")
	if not bond_sane(bond):
		raise rpc_lib.RPCException("Bond not sane.")
	if not Verify.verify(bond=bond):
		raise rpc_lib.RPCException("Invalid bond.")
	
	if BlacklistDB.try_to_redeem(bond=bond, address=address):
		return True # Success!
	else:
		raise rpc_lib.RPCException("Bond already used.")

def bond_sane(bond):
	# Make sure someone's not trying to make us verify a 15 MB cat GIF.
	print "WARNING: BondAuth.bond_sane not yet implemented"
	return True # Cat GIFs are okay for now...

def valid_address(address):
	# Make sure this is actually a bitcoin address
	print "WARNING: BondAuth.valid_address not yet implemented"
	return True
