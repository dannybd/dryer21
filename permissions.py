"""
permissions.py

This program launches all the others.
It also chmods everything in /jail to set the bits appropriately.
"""

import os, sys

# This is a global listing of all the processes we need to launch.
processes = {}

# These are all the resources.
resources = {}

class Process:
	def __init__(self, name, binary_path, has_rpc=False):
		# Store ourself in the global listing.
		assert name not in processes
		processes[name] = self
		self.name, self.binary_path = name, binary_path
		# If RPC is required, add an associated resource.
		self.rpc_resource = Resource("/rpc/" + name, owner=self)
		self.access = []

	def grant(self, resource):
		self.access.append(resource)

class Resource:
	def __init__(self, path, owner=None):
		# Store ourselves.
		assert path not in resources
		resources[path] = self
		self.path = path
		self.owner = owner

# This function lets a given process have access to a given resource.
def grant(name, path):
	processes[name].grant(resources[path])

# This function lets caller have access to server's RPC socket.
def grant_rpc(caller, server):
	processes[caller].grant(processes[server].rpc_resource)

# This function computes UIDs and GIDs for each process and resource.
def compute_tables():
	base_uid = 10000
	base_gid = 20000
	# Sequentially assign UIDs and GIDs to processes and resources.
	for process in processes.values():
		base_uid += 1
		process.uid = base_uid
	for resource in resources.values():
		base_gid += 1
		resource.gid = base_gid
	# Figure out the owners.
	for resource in resources.values():
		resource.uid = 0 if resource.owner is None else resource.owner.uid
	# Grant each process all its groups.
	for process in processes.values():
		process.groups = [resource.gid for resource in process.access]

def format_tables():
	s = ["# Processes"]
	for process in sorted(processes.values(), key=lambda x: x.uid):
		s.append("%s: UID=%i GIDs=[%s]" % (process.name, process.uid, ", ".join(map(str, process.groups))))
	s.append("# Resources")
	for resource in sorted(resources.values(), key=lambda x: x.path):
		s.append("%s: UID=%i GID=%i" % (resource.path, resource.uid, resource.gid))
	return "\n".join(s)

# Declare all the processes.
Process("FrontEnd", "/code/front_end.py")
Process("QuoteGen", "/code/quote_gen.py", has_rpc=True)
Process("IssueBond", "/code/issue_bond.py", has_rpc=True)
Process("Database", "/code/database.py", has_rpc=True)
Process("Checker", "/code/payment_checker.py", has_rpc=True)
Process("Signer", "/code/token_signer.py", has_rpc=True)

# Declare all the resources.
Resource("/global/master_public_key")
Resource("/global/master_private_key")
Resource("/global/token_public_key")
Resource("/global/token_private_key")

# Declare which processes have access to which resources.
grant_rpc("FrontEnd", "QuoteGen")
grant_rpc("FrontEnd", "IssueBond")
grant_rpc("QuoteGen", "Database")
grant_rpc("IssueBond", "Checker")
grant_rpc("IssueBond", "Signer")
grant_rpc("IssueBond", "Database")

grant("QuoteGen", "/global/master_public_key")
grant("Checker", "/global/master_public_key")
grant("Signer", "/global/master_private_key")

compute_tables()
print format_tables()

