import logging
import re
import secrets
import os
from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from functools import wraps
from datetime import datetime

# Set up logging to file and console
logging.basicConfig(level=logging.WARNING,
					format='%(asctime)s %(levelname)s:%(message)s',
					datefmt='%Y-%m-%d %H:%M:%S',
					handlers=[logging.FileHandler("app.log"),
							  logging.StreamHandler()])

app = Flask(__name__)
app.config["MONGO_URI"] = os.environ.get("DATABASE_URI")
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')

mongo = PyMongo(app)

def require_api_key(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		# Check for 'Authorization' in headers and 'aid' in JSON body
		api_key = request.headers.get('Authorization')
		aid = request.json.get('aid') if request.json else None 

		if api_key and aid:
			# Verify API key and Account ID
			account = mongo.db.accounts.find_one({"aid": aid, "api_key": api_key, "status": "Enabled"})
			if not account:
				app.logger.warning("Unauthorized or inactive account")
				return jsonify({"message": "Unauthorized or inactive account"}), 401
		else:
			app.logger.warning("Missing API key or Account ID")
			return jsonify({"message": "Missing API key or Account ID"}), 400

		return f(*args, **kwargs)
	return decorated_function

def generate_api_key():
	# Generates a secure, random API key
	return secrets.token_urlsafe(16)

@app.route('/admin/api_key/<aid>', methods=['POST'])
def create_api_key(aid):
	# Generates a new API key
	api_key = generate_api_key()
	# Prepares the account data with the API key, account ID, and enabled status
	account_data = {'aid': aid, 'api_key': api_key, 'status': 'Enabled'}
	# Inserts the account data into the MongoDB accounts collection
	mongo.db.accounts.insert_one(account_data)
	app.logger.info(f"API key created for aid {aid}")
	return jsonify({'aid': aid, 'api_key': api_key, 'message': 'API key created successfully'}), 200

def is_numeric(value):
	try:
		float(value)
		return True
	except ValueError:
		return False

def is_valid_date(value, date_format='%Y-%m-%d'):
	try:
		datetime.strptime(value, date_format)
		return True
	except ValueError:
		return False

def is_valid_ip(value):
	# Regular expression to validate IPv4 address
	ipv4_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
	return bool(ipv4_pattern.match(value))

# Update the list of required fields based on the latest requirements
required_fields = ['aid', 'first', 'last', 'email']

@app.route('/api/leads', methods=['POST'])
@require_api_key
def add_lead():
	data = request.json
	app.logger.info(f"Received lead submission: {data}")

	# Check for missing required fields in the request
	missing_fields = [field for field in required_fields if field not in data]
	if missing_fields:
		app.logger.warning(f"Missing required fields: {missing_fields}")
		return jsonify({'message': f'Missing required fields: {", ".join(missing_fields)}'}), 400
	
	# Validate field formats
	mortgage_balance_valid = is_numeric(data.get("mortgage_balance"))
	property_value_valid = is_numeric(data.get("property_value"))
	opt_in_date_valid = is_valid_date(data.get("opt_in_date"))
	ip_address_valid = is_valid_ip(data.get("ip_address"))
	
	if not mortgage_balance_valid or not property_value_valid or not opt_in_date_valid or not ip_address_valid:
		app.logger.error("Invalid data format in submission")
		# Respond with an appropriate error message
		# ...

	# Fetch account details based on 'aid' to include 'source' and 'vertical'
	account_info = mongo.db.accounts.find_one({"aid": data['aid']})
	if not account_info or account_info['status'] != 'Enabled':
		app.logger.error(f"Account not found or not enabled for aid {data['aid']}")
		return jsonify({"message": "Account not found or not enabled"}), 404

	# Since 'source' and 'vertical' are not submitted with the lead, but are essential,
	# we add them from the account_info
	data['source'] = account_info['source']
	data['vertical'] = account_info['vertical']
	
	# Inserting the lead into the 'leads' collection
	result = mongo.db.leads.insert_one(data)
	app.logger.info(f"Lead added successfully: {result.inserted_id}")
	return jsonify({'message': 'Lead added successfully', 'id': str(result.inserted_id)}), 201

if __name__ == '__main__':
	app.logger.debug("Starting Flask application")
	app.run(host='0.0.0.0', port=5024)
