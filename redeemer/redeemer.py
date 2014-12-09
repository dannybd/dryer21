from flask import Flask
from flask import make_response, render_template, request, json, url_for
jsonify = json.jsonify

app = Flask(__name__)

app.add_url_rule(
	'/favicon.ico',
	redirect_to=url_for('static', filename='favicon.ico')
)

@app.route('/')
def index():
	return render_template('redeemer.html')

# FIXME: Don't use GET
@app.route('/bond', methods=['GET', 'POST'])
def fetch_protobond():
	bond = request.args.get('bond', None)
	to_addr = request.args.get('to_addr', None)
	if not bond or not to_addr:
		return jsonify(error=True, success=False)
	return jsonify(success=True, msg='Thanks!')

if __name__ == '__main__':
	app.run(port=9002)
