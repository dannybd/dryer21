"""
seller.py

Contains the flask app which runs the seller frontend
Makes RPC calls to other code which crunches stuff, and passes the results back to the client.
"""
from flask import Flask
from flask import make_response, render_template, request, json, url_for
jsonify = json.jsonify

from rpc_clients.GenQuote import gen_quote
from rpc_clients.IssueProtobond import issue_protobond

app = Flask(__name__)
# Restrict uploading files larger than 10kB.
# Tokens are ~1kB, but this prevents cat GIF uploads.
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024

@app.route('/')
@app.route('/index')
def index():
	return render_template('seller.html')

@app.route('/connect', methods=['GET', 'POST'])
def fetch_connect():
	return jsonify(success=True)

@app.route('/quote', methods=['POST'])
def fetch_quote():
	token = request.form.get('token', None)
	addr, price, mock = None, None, False
	try:
		(addr, price) = gen_quote(token=token)
	except Exception, e:
		mock = True
		print 'Using server-side mock mode'
		(addr, price) = ('1DRYER21DRYER21DRYER21', '0.1BTC')
	finally:
		return jsonify(token=token,addr=addr,price=price,mock=mock)

@app.route('/protobond', methods=['POST'])
def fetch_protobond():
	token = request.form.get('token', None)
	protobond, mock = None, False
	try:
		protobond = issue_protobond(token)
	except Exception, e:
		mock = True
		print 'Using server-side mock mode'
		from random import randint
		if randint(1, 4) != 1:
			return jsonify(error='No bitcoin yet...',mock=mock)
		protobond = 'mock protobond goes here but validation is going to fail anyway because this is not aware of the nonce used'
	finally:
		return jsonify(protobond=protobond,mock=mock)

@app.errorhandler(413)
def request_entity_too_large(error):
	return 'The token you tried to upload was too large!', 413

if __name__ == '__main__':
	# FIXME: REMOVE DEBUG MODE IN PRODUCTION
	import sys
	app.debug = '--debug' in sys.argv[1:]
	app.run(port=9001)
