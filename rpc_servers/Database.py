"""
rpc_servers.Database
"""

import rpc_lib
import sqlite3

rpc_lib.set_rpc_socket_path("rpc/Database/sock")
conn = sqlite3.connect("data/seller_database/seller_database.db")

@rpc_lib.expose_rpc
def f(x):
	return x+1

