from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
import yaml
import os
import psutil
import requests
import socket
from healthcheck import HealthCheck, EnvironmentDump
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)
health = HealthCheck()
with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)


metrics.info('app_info', 'Application info', version='1.0.3')

SHEDDER_HOST = "0.0.0.0"
SHEDDER_PORT = "3004"


def is_running():
	return True, "is running"

health.add_check(is_running)

writerHost = "0.0.0.0"
writerPort = "3001"

if 'writerHost' in os.environ:
	writerHost = os.environ['writerHost']

if 'writerPort' in os.environ:
	writerPort = os.environ['writerPort']

@app.route('/api/_memory/updateIP', methods=['GET'])
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

@app.route('/api/_memory/constructHeavyDict', methods=['GET'])
def construct_heavy_dict():
	memoryFiller = {}
	repeat = int(request.args['repeat'])
	for i in range(repeat):
		memoryFiller[i] = 'vidit'*1024
	return jsonify({'result' : "Created a huge dictionary"})

@app.route('/api/_memory/dbWrite', methods=['POST'])
def db_write():
	return requests.post('http://' + writerHost + ':' + writerPort + '/_writeName').content
 	

if __name__ == '__main__':
	host = "0.0.0.0"
	port = 3002
	if 'summerHost' in os.environ:
		host = os.environ['summerHost']
	if 'summerPort' in os.environ:
		port = os.environ['summerPort']
	if 'shedderHost' in os.environ:
		SHEDDER_HOST = os.environ['shedderHost']
	if 'shedderPort' in os.environ:
		SHEDDER_PORT = os.environ['shedderPort']

	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=False, threaded=True)
	# app.run(host=locationMappings['summer']['url'], port=locationMappings['summer']['port'], debug=True)