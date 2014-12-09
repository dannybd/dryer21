from flask import Flask
from flask import make_response, redirect, render_template, request, json, url_for
jsonify = json.jsonify

app = Flask(__name__)

@app.route('/')
def index():
	return render_template('redeemer.html')

@app.route('/bond', methods=['GET', 'POST'])
def redeem_bond():
	if request.method == 'GET':
		return redirect(url_for(''))
	bond = request.args.get('bond', None)
	if not bond:
		return render_template('bond_error.html', err_msg='No bond supplied!')
	to_addr = request.args.get('to_addr', None)
	if not to_addr:
		return render_template('bond_error.html', err_msg='No destination bitcoin address supplied!')
	return render_template('bond_success.html', to_addr=to_addr)

if __name__ == '__main__':
	app.run(port=9002)
