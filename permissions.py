"""
permissions.py

This program launches all the others.
It also chmods everything in the jail to set the bits appropriately.
"""

import os, sys

# This is a special user we promise will never have any privs for anything.
NO_PRIVS = 999999

# This is a global listing of all the processes we need to launch.
processes = {}

# These are all the resources.
resources = {}

class Process:
	def __init__(self, name, binary_path, arguments=[], has_rpc=False):
		# Store ourself in the global listing.
		assert name not in processes
		processes[name] = self
		self.name, self.binary_path, self.arguments = name, binary_path, arguments
		# If RPC is required, add an associated resource.
		if has_rpc:
			self.rpc_resource = Resource("/dryer21/rpc/" + name, owner=self)
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
			print "%s <- UID=%i GID=%i" % (path, uid, gid)
			os.chown(path, uid, gid)
			# Set the permission bits.
			if os.path.isdir(path):
				os.chmod(path, 0750) # r-xr-x---
			else:
				os.chmod(path, 0660) # rw-rw----
	print "Spawning processes."
	wait_list = []
	for process in processes.values():
		pid = os.fork()
		if pid == 0:
			# Change into the dryer21 directory.
			os.chdir("/dryer21")
			# Drop permissions.
			os.setresgid(NO_PRIVS, NO_PRIVS, NO_PRIVS)
			os.setgroups(process.groups)
			os.setresuid(process.uid, process.uid, process.uid)
			# Now launch python on the given script.
			os.execve("/usr/bin/python", ["python", process.binary_path] + process.arguments, {"HOME": "/nonexistant"})
		else:
			wait_list.append(pid)
	print "Waiting for all children to die."
	for pid in wait_list:
		os.waitpid(pid, 0)
	print "Exiting."

# Declare all the processes.
Process("FrontEnd", "/dryer21/code/FrontEnd.py")
db = Process("Database", "/dryer21/code/rpc_lib.py", ["--launch", "rpc_servers.Database"], has_rpc=True)

Resource("/dryer21/data/seller_database", owner=db)

grant_rpc("FrontEnd", "Database")

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

