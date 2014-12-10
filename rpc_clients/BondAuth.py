import rpc_lib

ctx = rpc_lib.RPCClient("rpc/BondAuth/sock")
bond_auth = ctx.make_stub("bond_auth")

