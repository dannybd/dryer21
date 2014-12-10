"""
rpc_servers.SellerDB
"""

import rpc_lib, sqlite3, time

rpc_lib.set_rpc_socket_path("rpc/SellerDB/sock")

@rpc_lib.expose_rpc
def get(token):
	conn = sqlite3.connect("data/seller_database/seller_database.db")
	conn.row_factory = sqlite3.Row
	try:
		rows = list(conn.execute("select address_index, address, price, timestamp, protobond_sent from transactions where token=?", (token,)))
		assert len(rows) <= 1
		if len(rows) == 0:
			return None
		return dict(rows[0])
	finally:
		conn.close()

@rpc_lib.expose_rpc
def put(token, index, address, price):
	conn = sqlite3.connect("data/seller_database/seller_database.db")
	try:
		row = (token, index, address, price, time.time(), 0)
		try:
			conn.execute("insert into transactions(token, address_index, address, price, timestamp, protobond_sent) values(?, ?, ?, ?, ?, ?)", row)
		except sqlite3.IntegrityError:
			# Couldn't insert the row, probably that token already exists.
			return False
		conn.commit()
		return True
	finally:
		conn.close()

@rpc_lib.expose_rpc
def mark_protobond_sent(token):
	conn = sqlite3.connect("data/seller_database/seller_database.db")
	try:
		try:
			conn.execute("update transactions set protobond_sent = protobond_sent + 1 where token = ?", (token,))
		except sqlite3.IntegrityError:
			return False
		conn.commit()
		return True
	finally:
		conn.close()

