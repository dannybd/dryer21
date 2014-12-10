#! /usr/bin/python
"""
setup_databases.py
"""

import sys
import sqlite3

if len(sys.argv) != 2:
	print "Usage: %s <jail root>"
	print
	print "Sets up the databases in the jail directory."
	exit(1)

jail_dir = sys.argv[1]

con = sqlite3.connect(jail_dir + "/dryer21/data/seller_database/seller_database.db")
con.execute("""
create table transactions (
	nonce text primary key,
	address text
)
""")

