import rpc_lib

ctx = rpc_lib.RPCClient("rpc/GenQuote/sock")
gen_quote = ctx.make_stub("gen_quote")
