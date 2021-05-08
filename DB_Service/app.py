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

app = Flask(__name__)
metrics = PrometheusMetrics(app)
health = HealthCheck()

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
letters = string.ascii_lowercase

@app.route('/metrics', methods=['GET'])
def get_metrics():
	used_mem = psutil.virtual_memory().percent
	used_cpu = psutil.cpu_percent()
	return jsonify({'memory': used_mem, 'cpu': used_cpu})

@app.route('/app/db/bulkRead', methods=['GET'])
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


@app.route('/api/db/_writeName', methods=['POST'])
def write_name():
	star = mongo.db.stars
	name = ''.join(random.choice(letters) for i in range(10))
	rank = random.randrange(1000)
	star.update({"name": name}, {"$set": {'rank': rank}}, upsert = True)   ## May need to modify this.
	return jsonify({'result' : 	''.join(star.find_one({"name": name}))})


@app.route('/api/db/bulkWrite', methods=['POST'])
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


	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=True, threaded=True)
	# app.run(host=locationMappings['writer']['url'], port=locationMappings['writer']['port'], debug=True)