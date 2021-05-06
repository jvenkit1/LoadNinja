from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
import yaml
import os
import requests
from healthcheck import HealthCheck, EnvironmentDump


app = Flask(__name__)
health = HealthCheck()
with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)


def is_running():
	return True, "is running"

health.add_check(is_running)

writerHost = "0.0.0.0"
writerPort = "3001"

if 'writerHost' in os.environ:
	writerHost = os.environ['writerHost']

if 'writerPort' in os.environ:
	writerPort = os.environ['writerPort']


@app.route('/api/memory/constructHeavyDict', methods=['GET'])
def construct_heavy_dict():
	memoryFiller = {}
	repeat = int(request.args['repeat'])
	for i in range(repeat):
		memoryFiller[i] = 'vidit'*1024
	return jsonify({'result' : "Created a huge dictionary"})

@app.route('/api/memory/dbWrite', methods=['POST'])
def db_write():
	return requests.post('http://' + writerHost + ':' + writerPort + '/_writeName').content
 	

if __name__ == '__main__':
	host = "0.0.0.0"
	port = 3002
	if 'summerHost' in os.environ:
		host = os.environ['summerHost']
	if 'summerPort' in os.environ:
		port = os.environ['summerPort']

	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=True)
	# app.run(host=locationMappings['summer']['url'], port=locationMappings['summer']['port'], debug=True)