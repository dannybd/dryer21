"""
rpc_servers.RedeemerDB
"""

import rpc_lib, sqlite3, time

rpc_lib.set_rpc_socket_path("rpc/RedeemerDB/sock")

@rpc_lib.expose_rpc
def try_to_redeem(bond, address):
	conn = sqlite3.connect("data/redeemer_database/redeemer_database.db")
	try:
		row = (bond.encode("hex"), address, 0)
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
	bond = bond.encode("hex")
	try:
		conn.execute("update transactions set fulfilled = 1 where bond = ?", (bond,))
		conn.commit()
	finally:
		conn.close()
	return True

@rpc_lib.expose_rpc
def get_unfulfilled_rows():
	conn = sqlite3.connect("data/redeemer_database/redeemer_database.db")
	conn.row_factory = sqlite3.Row
	try:
		cursor = conn.execute("select * from transactions where fulfilled = 0")
		rows = map(dict, cursor)
		for row in rows:
			row["bond"] = row["bond"].decode("hex")
		return rows
	finally:
		conn.close()

