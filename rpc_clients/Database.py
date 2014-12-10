"""
rpc_clients.Database
"""

import rpc_lib

ctx = rpc_lib.RPCClient("rpc/Database/sock")
add_to_counter = ctx.make_stub("add_to_counter")

