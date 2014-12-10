"""
rpc_clients.Database
"""

import rpc_lib

ctx = rpc_lib.RPCClient("rpc/Database/sock")
get = ctx.make_stub("get")
put = ctx.make_stub("put")
mark_protobond_sent = ctx.make_stub("mark_protobond_sent")

