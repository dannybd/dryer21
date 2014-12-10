"""
redeemer.py

Contains the flask app which runs the redeemer frontend
Makes RPC calls to other code which crunches stuff, and passes the results back to the client.
"""
import sys
import traceback
from flask import Flask
from flask import make_response, redirect, render_template, request, json, url_for
jsonify = json.jsonify

import rpc_lib
from rpc_clients import BondRedeemer

app = Flask(__name__)
# Restrict uploading files larger than 10kB.
# Tokens are ~1kB, but this prevents cat GIF uploads.
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024

@app.route('/')
def index():
	return render_template('redeemer.html')

@app.route('/bond', methods=['GET', 'POST'])
def redeem_bond():
	if request.method == 'GET':
		return redirect(url_for('index'))
	bond_file = request.files['bond_file']
	if not bond_file:
		return bond_error('No bond supplied!')
	bond = bond_file.read()
	if not bond:
		return bond_error('Bond file empty!')
	to_addr = request.form.get('to_addr', None)
	if not to_addr:
		return bond_error('No destination bitcoin address supplied!')
	# We've confirmed that the user has properly supplied a bond and an address
	BondRedeemer.bond_redeem(bond=bond, address=to_addr)
	return render_template('bond_success.html', to_addr=to_addr)

def bond_error(err_msg=None):
	return render_template('bond_error.html', err_msg=err_msg)

@app.errorhandler(rpc_lib.RPCException)
def rpc_lib_RPCException(error):
	print traceback.format_exc()
	raise error

@app.errorhandler(413)
def request_entity_too_large(error):
	return bond_error('The file you tried to upload was too large!'), 413

if __name__ == '__main__':
	app.debug = '--debug' in sys.argv[1:]
	app.run(port=9002)
