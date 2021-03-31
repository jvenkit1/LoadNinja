from flask import Flask
from flask import jsonify
from flask import request
import yaml
import os
import hashlib

app = Flask(__name__)
with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)


@app.route('/hashFile', methods=['GET'])
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

@app.route('/generateLoad', methods=['GET'])
def generate_multiply_load():
	repeat = int(request.args['repeat'])
	for _ in range(repeat):
		pr = 213123  # generates some load
		x = pr * pr
		pr = pr + 1
	return jsonify({'result': x})

if __name__ == '__main__':
	host = os.environ['hasherHost']
	port = os.environ['hasherPort']
	app.run(host=host, port=port, debug=True)