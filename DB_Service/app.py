from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
import yaml
import os
import random
import psutil
import string
from healthcheck import HealthCheck, EnvironmentDump
from prometheus_flask_exporter import PrometheusMetrics

import socket
import requests

app = Flask(__name__)
metrics = PrometheusMetrics(app)
health = HealthCheck()

metrics.info('app_info', 'Application info', version='1.0.3')

SHEDDER_HOST = "0.0.0.0"
SHEDDER_PORT = "3004"

with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)

# app.config['MONGO_DBNAME'] = locationMappings["db"]["name"]
# app.config['MONGO_URI'] = 'mongodb://' + locationMappings["db"]["url"] + ':' + str(locationMappings["db"]["port"]) + '/'+ locationMappings["db"]["name"]

def is_running():
	return True, "is running"

health.add_check(is_running)


dbName = "test"
dbURL = "0.0.0.0"
dbPort = 27017

if 'dbName' in os.environ:
	dbName = os.environ['dbName']

if 'dbURL' in os.environ:
	dbURL = os.environ['dbURL']

if 'dbPort' in os.environ:
	dbPort = os.environ['dbPort']

app.config['MONGO_DBNAME'] = dbName
app.config['MONGO_URI'] = 'mongodb://' + dbURL + ':' + str(dbPort) + '/'+ dbName

mongo = PyMongo(app)
mongo.db.authenticate(name='root', password='6VPFJn4kJa', source='admin')
letters = string.ascii_lowercase

@app.route('/api/_db/updateIP', methods=['GET'])
def update_ip():
	url = "http://" + SHEDDER_HOST + ":" + SHEDDER_PORT + "/api/shed/updatepodslist"
	url = url.replace(' ', '')
	print("Querying api at address ", url)
	data = {}
	data['ip'] = socket.gethostbyname(socket.gethostname())
	try:
		r = requests.post(url = url, data = data)
	except:
		print("Couldn't update shedder with the IP of this pod")
	return jsonify({'result': 'Sent the IP'})

@app.route('/internal/metrics', methods=['GET'])
def get_metrics():
	used_mem = psutil.virtual_memory().percent
	used_cpu = psutil.cpu_percent()
	return jsonify({'memory': used_mem, 'cpu': used_cpu})

@app.route('/api/_db/bulkRead', methods=['GET'])
def get_all_stars():
	star = mongo.db.stars
	repeat = int(request.args['repeat'])
	for _ in range(repeat):
		name = ''.join(random.choice(letters) for i in range(10))
		rank = random.randrange(1000)
		star.update({"name": name}, {"$set": {'rank': rank}}, upsert = True)

	output = []
	for s in star.find():
		output.append({'name' : s['name'], 'rank' : s['rank']})
	return jsonify({'result' : output})


@app.route('/api/_db/_writeName', methods=['POST'])
def write_name():
	star = mongo.db.stars
	name = ''.join(random.choice(letters) for i in range(10))
	rank = random.randrange(1000)
	star.update({"name": name}, {"$set": {'rank': rank}}, upsert = True)   ## May need to modify this.
	return jsonify({'result' : 	''.join(star.find_one({"name": name}))})


@app.route('/api/_db/bulkWrite', methods=['POST'])
def add_star():
	star = mongo.db.stars
	repeat = int(request.args['repeat'])
	for _ in range(repeat):
		name = ''.join(random.choice(letters) for i in range(10))
		rank = random.randrange(1000)
		star.update({"name": name}, {"$set": {'rank': rank}}, upsert = True)

	star.remove()
	return jsonify({'result' : 'Upserted ' + str(repeat) + ' documents in DB and removed all of them'})

if __name__ == '__main__':
	host = "0.0.0.0"
	port = 3001
	if 'writerHost' in os.environ:
		host = os.environ['writerHost']
	if 'writerPort' in os.environ:
		port = os.environ['writerPort']
	if 'shedderHost' in os.environ:
		SHEDDER_HOST = os.environ['shedderHost']
	if 'shedderPort' in os.environ:
		SHEDDER_PORT = os.environ['shedderPort']

	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=False, threaded=True)
	# app.run(host=locationMappings['writer']['url'], port=locationMappings['writer']['port'], debug=True)