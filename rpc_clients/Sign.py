import rpc_lib

ctx = rpc_lib.RPCClient("rpc/Sign/sock")
sign = ctx.make_stub("sign")
