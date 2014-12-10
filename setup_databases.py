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

seller_db_path = jail_dir + "/dryer21/data/seller_database/seller_database.db"
redeemer_db_path = jail_dir + "/dryer21/data/redeemer_database/redeemer_database.db"

try:
	os.unlink(seller_db_path)
	os.unlink(redeemer_db_path)
except OSError:
	pass

# Create the seller database.
con = sqlite3.connect(seller_db_path)
con.execute("""
create table transactions (
	token text primary key,
	address_index text,
	address text,
	price integer,
	timestamp real,
	protobond_sent integer
);
""")
con.commit()
con.close()

# Create the redeemer database.
con = sqlite3.connect(redeemer_db_path)
con.execute("""
create table transactions (
	bond text primary key,
	address text,
	fulfilled integer
);
""")
con.commit()
con.close()

