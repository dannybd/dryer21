"""
Collector: Moves BTC from the per-client generated payment reception wallets into the mixing wallet.into the mixing wallet.
Iterates through the database to find entries where the bond has been sent. After double-checking that payment has indeed been sent, send it over to the mix-in wallet.

Requires:
- Database RPC
- Check RPC
- BTC seed (master private key)
"""
import global_storage
import bitcoin

import rpc_lib
from rpc_clients import Check, SellerDB

def collect():
	seed = global_storage.get_collector_master_private_key()
	for row in SellerDB.get_rows_with_protobond_sent():
		# A row is a dict with keys address and address_index
		address, index = row['address'], row['address_index']
		assert bitcoin.electrum_address(seed, index) == address
		if Check.check(address, global_storage.bitcoin_price): # Double-check that payment has indeed been sent
			privkey = bitcoin.electrum_privkey(seed, index)
			send_whole_wallet(privkey, global_storage.get_mixin_address())

def send_whole_wallet(fromprivkey, toaddr):
	transaction_fee = 20000 # .0002 BTC
	fromaddress = privtoaddr(fromprivkey)
	balance = sum(transaction['value'] for transaction in bitcoin.unspent(address))
	assert balance >= transaction_fee
	tx = bitcoin.mktx(bitcoin.history(fromaddress), [{'value': balance - transaction_fee, 'address': toaddr}])
	signed_tx = bitcoin.sign(tx, 0, fromprivkey)
	bitcoin.pushtx(signed_tx)

if __name__ == "__main__":
	import time
	while True:
		time.sleep(5)
		collect()
