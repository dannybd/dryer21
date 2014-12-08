"""
check.py

Checks whether we've been paid.
In particular, exposes a method check that does the following:
Given a bitcoin address and a price, checks whether that wallet contains that amount. 
This implementation relies on blockchain.info for information about wallet balances. This means that the runners of blockchain.info could easily steal all our money. Were we actually running this service for real we'd instead have a bitcoin client running on the server with a local copy of the blockchain.
Additionally this implementation doesn't check that a transaction has confirmed yet. Again, were we running the service for real we'd be sure the transactions had confirmed.
"""
import bitcoin

@expose_rpc
def check(addr, price):
	unspent_transactions = bitcoin.unspent(addr) # Returns a list of dicts with the keys 'output' and 'value'
	total_balance = sum(transaction['value'] for transaction in unspent_transactions) # in satoshi
	return total_balance >= price
