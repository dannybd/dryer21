"""
rpc_servers.SellerDB
"""

import rpc_lib, sqlite3, time

rpc_lib.set_rpc_socket_path("rpc/SellerDB/sock")

@rpc_lib.expose_rpc
def get(token):
	conn = sqlite3.connect("data/seller_database/seller_database.db")
	conn.row_factory = sqlite3.Row
	token = token.encode("hex")
	try:
		rows = list(conn.execute("select address_index, address, price, timestamp, protobond_sent from transactions where token=?", (token,)))
		assert len(rows) <= 1
		if len(rows) == 0:
			return None
		row = dict(rows[0])
		row["address_index"] = int(row["address_index"])
		row["address"] = row["address"].decode("hex")
		return row
	finally:
		conn.close()

@rpc_lib.expose_rpc
def put(token, index, address, price):
	conn = sqlite3.connect("data/seller_database/seller_database.db")
	try:
		row = (token.encode("hex"), str(index), address.encode("hex"), price, time.time(), 0)
		# This next line might throw sqlite3.IntegrityError, but that's okay.
		conn.execute("insert into transactions(token, address_index, address, price, timestamp, protobond_sent) values(?, ?, ?, ?, ?, ?)", row)
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

@rpc_lib.expose_rpc
def get_rows_with_protobond_sent():
	conn = sqlite3.connect("data/seller_database/seller_database.db")
	conn.row_factory = sqlite3.Row
	try:
		rows = map(dict, conn.execute("select address_index, address, price, timestamp, protobond_sent from transactions where protobond_sent > 0",))
		for row in rows:
			row["address_index"] = int(row["address_index"])
			row["address"] = row["address"].decode("hex")
		return rows
	finally:
		conn.close()

