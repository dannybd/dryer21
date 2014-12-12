"""
dispenser: Dispenses bitcoins

Iterates through unfulfilled rows of the RedeemerDB, marks them as fulfilled, and then sends BTC.

Requires:
- Mix-out wallet private key (for sending bitcoins)
- RedeemerDB RPC (to find where to send bitcoins)
"""

import bitcoin
from rpc_clients import RedeemerDB
import global_storage

def dispense():
	for row in RedeemerDB.get_unfulfilled_rows():
		# A row is a dict with keys 'bond', 'address', and 'fulfilled'.
		assert row['fulfilled'] == 0 
		print "Unfulfilled row:", row
		RedeemerDB.mark_fulfilled(bond=row['bond'])
		send(global_storage.get_dispenser_private_key(), row['address'], global_storage.bond_value)

def send(fromprivkey, toaddr, value):
	transaction_fee = 20000
	tx = bitcoin.mksend(bitcoin.history(bitcoin.privtoaddr(fromprivkey)), [{'value': value, 'address': toaddr}], bitcoin.privtoaddr(fromprivkey), transaction_fee)
	signed_tx = bitcoin.sign(tx, 0, fromprivkey)
	bitcoin.pushtx(signed_tx)

if __name__ == "__main__":
	while True:
		import time
		time.sleep(60)
		dispense()
