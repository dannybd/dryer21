from flask import Flask
from flask import make_response, render_template, request, json
jsonify = json.jsonify

app = Flask(__name__)

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/init', methods=['GET', 'POST'])
def fetch_init():
	return jsonify(success=True)

@app.route('/quote', methods=['POST'])
def fetch_quote():
	token = request.args.get('token', None)
	return jsonify(token=token,price='0.1BTC',addr='1TORTORTORTOR')

@app.route('/protobond', methods=['POST'])
def fetch_protobond():
	token = request.args.get('token', None)
	from random import randint
	if randint(1, 4) != 1:
		return jsonify(error='No bitcoin yet...')
	protobond = 'protobond goes here'
	return jsonify(protobond=protobond)

if __name__ == '__main__':
	app.run(port=9001)
