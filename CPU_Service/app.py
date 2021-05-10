from flask import Flask
from flask import jsonify
from flask import request
import yaml
import psutil
import json
import os
import socket
import hashlib
import requests

from healthcheck import HealthCheck, EnvironmentDump
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)
health = HealthCheck()
envdump = EnvironmentDump()
metrics.info('app_info', 'Application info', version='1.0.3')

SHEDDER_HOST = "0.0.0.0"
SHEDDER_PORT = "3004"

with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)


def is_running():
	return True, "is running"

health.add_check(is_running)

@app.route('/api/_cpu/updateIP', methods=['GET'])
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


@app.route('/api/_cpu/hashFile', methods=['GET'])
# @metrics.counter(
#     'cnt_collection', 'Number of invocations per collection', labels={
#         'collection': lambda: request.view_args['collection_id'],
#         'status': lambda resp: resp.status_code
#     })
def hash_file():
	repeat = int(request.args['repeat'])
	for _ in range(repeat):
		h = hashlib.sha512()
		with open("./test.mp3", 'rb') as file:
			# loop till the end of the file
			chunk = 0
			while chunk != b'':
				# read only 1024 bytes at a time
				chunk = file.read(1024)
				h.update(chunk)
	return jsonify({'hash' : h.hexdigest()})

@app.route('/api/_cpu/generateLoad', methods=['GET'])
def generate_multiply_load():
	repeat = int(request.args['repeat'])
	for _ in range(repeat):
		pr = 213123  # generates some load
		x = pr * pr
		pr = pr + 1
	return jsonify({'result': x})

if __name__ == '__main__':
	host = "0.0.0.0"
	port = 3000
	if 'hasherHost' in os.environ:
		host = os.environ['hasherHost']
	if 'hasherPort' in os.environ:
		port = os.environ['hasherPort']
	if 'shedderHost' in os.environ:
		SHEDDER_HOST = os.environ['shedderHost']
	if 'shedderPort' in os.environ:
		SHEDDER_PORT = os.environ['shedderPort']

	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=False, threaded=True)