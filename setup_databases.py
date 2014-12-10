#! /usr/bin/python
"""
setup_databases.py
"""

import sys, os, sqlite3

if len(sys.argv) != 2:
	print "Usage: %s <jail root>"
	print
	print "Sets up the databases in the jail directory."
	print "WARNING: Overwrites whatever database you currently have!"
	exit(1)

jail_dir = sys.argv[1]

db_path = jail_dir + "/dryer21/data/seller_database/seller_database.db"

try:
	os.unlink(db_path)
except OSError:
	pass

con = sqlite3.connect(db_path)
con.execute("""
create table transactions (
	token text primary key,
	address_index integer,
	address text,
	price integer,
	timestamp real,
	protobond_sent integer
);
""")

