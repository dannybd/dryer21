"""
rpc_clients.Check
"""

import rpc_lib

ctx = rpc_lib.RPCClient("rpc/Check/sock")
check = ctx.make_stub("check")

