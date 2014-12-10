import rpc_lib

ctx = rpc_lib.RPCClient("rpc/BondRedeemer/sock")
bond_redeem = ctx.make_stub("bond_redeem")

