"""
permissions.py

This program launches all the others.
It also chmods everything in /jail to set the bits appropriately.
"""

import os, sys

JAIL_DIR = "/jail/"

# This is a special user we promise will never have any privs for anything.
NO_PRIVS = 999999

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
		if has_rpc:
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

def launch_sequence():
	print "Setting permissions on resources."
	for resource in resources.values():
		path = JAIL_DIR + resource.path
		uid, gid = resource.uid, resource.gid
		# Set the owner bits.
		print "%s <- UID=%i GID=%i" % (path, uid, gid)
		os.chown(path, uid, gid)
		# Set the permission bits.
		os.chmod(path, 0750) # r-xr-x--- # FIXME 0750 != r-xr-x---
	print "Spawning processes."
	for process in processes.values():
		if os.fork() == 0:
			# Drop permissions.
			os.setresgid(NO_PRIVS, NO_PRIVS, NO_PRIVS)
			os.setgroups(process.groups)
			os.setresuid(process.uid, process.uid, process.uid)
			# Now launch.
			os.execve(process.binary_path, (), {})

# Declare all the processes.
Process("FrontEnd", "/code/front_end.py")
Process("QuoteGen", "/code/quote_gen.py", has_rpc=True)
Process("IssueBond", "/code/issue_bond.py", has_rpc=True)
Process("Database", "/code/database.py", has_rpc=True)
Process("Checker", "/code/payment_checker.py", has_rpc=True)
Process("Signer", "/code/token_signer.py", has_rpc=True)

# Declare all the resources.
Resource("/global/btc_master_public_key") # Used to deterministically generate Bitcoin addresses (without generating the corresponding private keys)
Resource("/global/btc_master_private_key") # Used with the master public key to deterministically generate Bitcoin addresses with the private keys
Resource("/global/bond_public_key") # Used to verify bonds
Resource("/global/bond_private_key") # Used to sign proto-bonds

# Declare which processes have access to which resources.
grant_rpc("FrontEnd", "QuoteGen")
grant_rpc("FrontEnd", "IssueBond")
grant_rpc("QuoteGen", "Database")
grant_rpc("IssueBond", "Checker")
grant_rpc("IssueBond", "Signer")
grant_rpc("IssueBond", "Database")

# QuoteGen needs to generate addresses for people to send BTC to. To generate these addresses deterministically it uses the master public key.
grant("QuoteGen", "/global/btc_master_public_key")

# The checker checks that people have paid. The database stores (for a particular session) the wallet index, not the public key, so that the private key doesn't have to be stored. This means the checker needs to convert from a wallet index to a public key, which requires the Bitcoin master public key.
grant("Checker", "/global/btc_master_public_key")

# The signer signs proto-bonds, so it needs the private key for signing.
grant("Signer", "/global/bond_private_key")

# If invoked directly, then we print out the tables.
if __name__ == "__main__":
	compute_tables()
	# If passed the single argument --launch, then launch the application.
	if len(sys.argv) == 2 and sys.argv[1] == "--launch":
		launch_sequence()
		exit()
	# Otherwise, print some information.
	print "# Usage: permissions.py [--launch]"
	print "# Prints UID/GID table when run without an argument."
	print "# If passed --launch, launches the entire application."
	print format_tables()

