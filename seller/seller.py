from flask import Flask
from flask import make_response, render_template, request, json, url_for
jsonify = json.jsonify

app = Flask(__name__)
# Restrict uploading files larger than 10kB. FIXME: Set to size of token in the future.
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024

@app.route('/')
@app.route('/index')
def index():
	return render_template('seller.html')

@app.route('/connect', methods=['GET', 'POST'])
def fetch_connect():
	return jsonify(success=True)

# FIXME: Don't use GET
@app.route('/quote', methods=['GET', 'POST'])
def fetch_quote():
	token = request.args.get('token', None)
	mock = False
	try:
		# FIXME: Use RPC once available
		from gen_quote import gen_quote
		(addr, price) = gen_quote(token=token)
	except Exception, e:
		mock = True
		(addr, price) = ('1DRYER21DRYER21DRYER21', '0.1BTC')
	finally:
		return jsonify(token=token,addr=addr,price=price,mock=mock)

# FIXME: Don't use GET
@app.route('/protobond', methods=['GET', 'POST'])
def fetch_protobond():
	token = request.args.get('token', None)
	mock = False
	try:
		# FIXME: Use RPC once available
		from issue_protobond import issue_protobond
		protobond = issue_protobond(token)
	except Exception, e:
		mock = True
		from random import randint
		if randint(1, 4) != 1:
			return jsonify(error='No bitcoin yet...',mock=mock)
		protobond = 'protobond goes here'
	finally:
		return jsonify(protobond=protobond,mock=mock)

@app.errorhandler(413)
def request_entity_too_large(error):
	return 'The token you tried to upload was too large!', 413

if __name__ == '__main__':
	app.run(port=9001)
