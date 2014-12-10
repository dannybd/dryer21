"""
rpc_servers.RedeemerDB
"""

import rpc_lib, sqlite3, time

rpc_lib.set_rpc_socket_path("rpc/RedeemerDB/sock")

@rpc_lib.expose_rpc
def try_to_redeem(bond, address):
	conn = sqlite3.connect("data/redeemer_database/redeemer_database.db")
	try:
		row = (bond, address, 0)
		conn.execute("insert into transactions(bond, address, fulfilled) values(?, ?, ?)", row)
		conn.commit()
		return True
	except sqlite3.IntegrityError:
		# This means the row is already in the database, and we report this by returning False.
		return False
	finally:
		conn.close()

@rpc_lib.expose_rpc
def mark_fulfilled(bond):
	conn = sqlite3.connect("data/redeemer_database/redeemer_database.db")
	try:
		conn.execute("update transactions set fulfilled = 1 where bond = ?", (bond,))
		conn.commit()
	finally:
		conn.close()
	return True

