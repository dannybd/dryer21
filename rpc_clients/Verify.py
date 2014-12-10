import rpc_lib

ctx = rpc_lib.RPCClient("rpc/Verify/sock")
verify = ctx.make_stub("verify")
