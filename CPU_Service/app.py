from flask import Flask
from flask import jsonify
from flask import request
import yaml
import psutil
import os
import hashlib

from healthcheck import HealthCheck, EnvironmentDump
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)
health = HealthCheck()
envdump = EnvironmentDump()


with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)


def is_running():
	return True, "is running"

health.add_check(is_running)

@app.route('/metrics', methods=['GET'])
def get_metrics():
	used_mem = psutil.virtual_memory().percent
	used_cpu = psutil.cpu_percent()
	return jsonify({'memory': used_mem, 'cpu': used_cpu})

@app.route('/api/_cpu/hashFile', methods=['GET'])
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
	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=True, threaded=True)