"""
permissions.py

This program launches all the others.
It also chmods everything in the jail to set the bits appropriately.
"""

import os, sys, time, collections

# This is a special user we promise will never have any privs for anything.
NO_PRIVS = 999999

# This is a global listing of all the processes we need to launch.
# We keep track of the order to track dependencies.
# We will launch processes in the order they are added to this dict.
processes = collections.OrderedDict()

# These are all the resources.
resources = {}

class Process:
	def __init__(self, name, binary_path, arguments=[]):
		# Store ourself in the global listing.
		assert name not in processes
		processes[name] = self
		self.name, self.binary_path, self.arguments = name, binary_path, arguments
		self.access = []
		self.rpc_resource = None

	def grant(self, resource):
		self.access.append(resource)

class Resource:
	def __init__(self, path, owner=None):
		# Store ourselves.
		assert path not in resources
		resources[path] = self
		self.path = path
		self.owner = owner

def declare_rpc_service(name):
	proc = Process(name, "/dryer21/code/rpc_lib.py", ["--launch", "rpc_servers." + name])
	# Set the processes' RPC resource.
	proc.rpc_resource = Resource("/dryer21/rpc/" + name, owner=name)

# This function lets a given process have access to a given resource.
def grant(name, path):
	processes[name].grant(resources[path])

# This function lets caller have access to server's RPC socket.
def grant_rpc(caller, server):
	processes[caller].grant(processes[server].rpc_resource)

# This function computes UIDs and GIDs for each process and resource.
def compute_tables():
	base_uid = 1000000000
	base_gid = 2000000000
	# Sequentially assign UIDs and GIDs to processes and resources.
	for process in processes.values():
		base_uid += 1
		process.uid = base_uid
	for resource in resources.values():
		base_gid += 1
		resource.gid = base_gid
	# Figure out the owners.
	for resource in resources.values():
		resource.uid = 0 if resource.owner is None else processes[resource.owner].uid
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
	print "Creating resource directories."
	for resource in resources.values():
		if not os.path.exists(resource.path):
			print "Creating: %s" % resource.path
			os.mkdir(resource.path)
	print "Setting permissions on resources."
	for resource in resources.values():
		uid, gid = resource.uid, resource.gid
		for leaf in os.listdir(resource.path) + ["."]:
			path = resource.path + "/" + leaf
			# Set the owner bits.
			os.chown(path, uid, gid)
			# Set the permission bits.
			if os.path.isdir(path):
				# Justification:
				os.chmod(path, 0750) # rwxr-x---
			else:
				os.chmod(path, 0640) # rw-r-----
	wait_list = []
	for process in processes.values():
		print "Spawning", process.name
		# Delete the RPC resource socket, if there happens to be an old one sitting around.
		# XXX: This code knows about the convention of rpc/Service/sock!
		if process.rpc_resource != None:
			if os.path.exists(process.rpc_resource.path + "/sock"):
				os.unlink(process.rpc_resource.path + "/sock")
		pid = os.fork()
		if pid == 0:
			# Change into the dryer21 directory.
			os.chdir("/dryer21")
			# Drop permissions.
			os.setresgid(NO_PRIVS, NO_PRIVS, NO_PRIVS)
			os.setgroups(process.groups)
			os.setresuid(process.uid, process.uid, process.uid)
			# Now launch python on the given script.
			os.execve("/usr/bin/python", ["python", process.binary_path] + process.arguments, {"HOME": "/nonexistant", "PYTHONPATH": "/dryer21/code"})
		else:
			# Wait for the child to finish setting up, if it has an rpc_resource.
			# This is necessary to prevent race conditions where future processes try to connect before this one is done setting up.
			if process.rpc_resource != None:
				# Currently I just use a little spin loop, which is good enough -- I'm not going to use inotify.
				while not os.path.exists(process.rpc_resource.path + "/sock"):
					time.sleep(0.1)
			wait_list.append(pid)
	for pid in wait_list:
		os.waitpid(pid, 0)
	print "Exiting."

# Declare all the processes, which will be launched in the declared order.
# NOTE: These MUST be declared in RPC dependency order!
declare_rpc_service("SellerDB")
declare_rpc_service("Sign")
declare_rpc_service("Check")
declare_rpc_service("IssueProtobond")
declare_rpc_service("GenQuote")
Process("Seller", "/dryer21/code/seller/seller.py")

declare_rpc_service("RedeemerDB")
declare_rpc_service("BondRedeemer")
Process("Redeemer", "/dryer21/code/redeemer/redeemer.py")
Process("Dispenser", "/dryer21/code/dispenser.py")

# Having access to a resource gives r-x, but being owner gives rwx.
# Unfortunately, sqlite3 appears to modify the directory somehow, so it needs to be an owner.
Resource("/dryer21/data/seller_database", owner="SellerDB")
Resource("/dryer21/data/redeemer_database", owner="RedeemerDB")
Resource("/dryer21/data/signing_private_key")
Resource("/dryer21/data/collector_master_public_key")
Resource("/dryer21/data/collector_master_private_key")
Resource("/dryer21/data/dispenser_address")
Resource("/dryer21/data/dispenser_private_key")
Resource("/dryer21/data/mixin_address")

grant("Sign", "/dryer21/data/signing_private_key")
grant("Dispenser", "/dryer21/data/dispenser_private_key")

grant_rpc("Seller", "GenQuote")
grant_rpc("Seller", "IssueProtobond")
grant_rpc("GenQuote", "SellerDB")
grant_rpc("IssueProtobond", "SellerDB")
grant_rpc("IssueProtobond", "Check")
grant_rpc("IssueProtobond", "Sign")
grant_rpc("Check", "SellerDB")

grant_rpc("Redeemer", "BondRedeemer")
grant_rpc("BondRedeemer", "RedeemerDB")
grant_rpc("Dispenser", "RedeemerDB")

# If invoked directly, then we print out the tables.
if __name__ == "__main__":
	compute_tables()
	print format_tables()
	# If passed the single argument --launch, then launch the application.
	if len(sys.argv) == 2 and sys.argv[1] == "--launch":
		launch_sequence()
		exit()
	# Otherwise, print some information.
	print "# Usage: permissions.py [--launch]"
	print "# Prints UID/GID table when run without an argument."
	print "# If passed --launch, launches the entire application."

