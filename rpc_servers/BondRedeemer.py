"""
BondRedeemer:

Redeeming a bond involves verifying that the bond is valid (i.e., something we signed) and unused (to be sure people aren't double-spending.) We do the former with Verify.verify and the latter with RedeemerDB.try_to_redeem.

Requires:
- RedeemerDB RPC (to add bonds to the blacklist / to-be-paid list)
"""

import rpc_lib

import Verify
from rpc_clients import RedeemerDB

rpc_lib.set_rpc_socket_path("rpc/BondRedeemer/sock")

@rpc_lib.expose_rpc
def bond_redeem(bond, address):
	"""
	Given a bond and an address, verifies the bond and then adds the bond and address to the RedeemerDB for later redemption.
	Returns True on success, raises exception on error.
	"""
	if not valid_address(address):
		raise rpc_lib.RPCException("Invalid address.")
	if not bond_sane(bond):
		raise rpc_lib.RPCException("Bond not sane.")
	if not Verify.verify(bond=bond):
		raise rpc_lib.RPCException("Invalid bond.")
	
	if RedeemerDB.try_to_redeem(bond=bond, address=address):
		return True # Success!
	else:
		raise rpc_lib.RPCException("Bond already used.")

def bond_sane(bond):
	# Make sure someone's not trying to make us verify a 15 MB cat GIF.
	print "WARNING: BondRedeemer.bond_sane not yet implemented"
	return True # Cat GIFs are okay for now...

def valid_address(address):
	# Make sure this is actually a bitcoin address
	print "WARNING: BondRedeemer.valid_address not yet implemented"
	return True
