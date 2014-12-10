import rpc_lib

ctx = rpc_lib.RPCClient("rpc/IssueProtobond/sock")
issue_protobond = ctx.make_stub("issue_protobond")
