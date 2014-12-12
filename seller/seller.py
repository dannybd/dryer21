"""
seller.py

Contains the flask app which runs the seller frontend
Makes RPC calls to other code which crunches stuff, and passes the results back to the client.
"""
import sys
import traceback
from flask import Flask
from flask import make_response, render_template, request, json, url_for
jsonify = json.jsonify

import rpc_lib
from rpc_clients import GenQuote, IssueProtobond
from global_storage import CryptoVars

app = Flask(__name__)
# Restrict uploading files larger than 10kB.
# Tokens are ~1kB, but this prevents cat GIF uploads.
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024

@app.route('/')
@app.route('/index')
def index():
	return render_template('seller.html')

@app.route('/Dryer21Client.py')
def download_client():
	response = make_response(render_template(
		'Dryer21Client.py.template',
		CryptoVars=CryptoVars,
	))
	response.headers['Content-Disposition'] = 'attachment; filename=Dryer21Client.py'
	return response

@app.route('/connect', methods=['GET', 'POST'])
def fetch_connect():
	return jsonify(success=True)

@app.route('/quote', methods=['POST'])
def fetch_quote():
	token = request.form.get('token', None)
	(addr, price) = GenQuote.gen_quote(token=token)
	return jsonify(token=token, addr=addr, price=price)

@app.route('/protobond', methods=['POST'])
def fetch_protobond():
	token = request.form.get('token', None)
	protobond = IssueProtobond.issue_protobond(token=token)
	return jsonify(protobond=protobond)

@app.errorhandler(rpc_lib.RPCException)
def rpc_lib_RPCException(error):
	print traceback.format_exc()
	raise error

@app.errorhandler(413)
def request_entity_too_large(error):
	return 'The token you tried to upload was too large!', 413

if __name__ == '__main__':
	app.debug = '--debug' in sys.argv[1:]
	app.run(port=9001)

