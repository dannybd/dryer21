"""
rpc_clients.RedeemerDB
"""

import rpc_lib

ctx = rpc_lib.RPCClient("rpc/RedeemerDB/sock")
try_to_redeem = ctx.make_stub("try_to_redeem")
mark_fulfilled = ctx.make_stub("mark_fulfilled")

