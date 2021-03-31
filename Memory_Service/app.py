from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
import yaml
import os
import requests

app = Flask(__name__)
with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)

mongo = PyMongo(app)

@app.route('/constructHeavyDict', methods=['GET'])
def construct_heavy_dict():
	memoryFiller = {}
	repeat = request.args['repeat']
	for i in range(repeat):
		memoryFiller[i] = 'vidit'*1024
	return jsonify({'result' : "Created a huge dictionary"})

@app.route('/dbWrite', methods=['POST'])
def db_write():
	return requests.post('http://' + os.environ['writerHost'] + ':' + os.environ['writerPort'] + '/_writeName').content
 	

if __name__ == '__main__':
		host = os.environ['summerHost']
		port = os.environ['summerPort']
		app.run(host=host, port=port, debug=True)
		# app.run(host=locationMappings['summer']['url'], port=locationMappings['summer']['port'], debug=True)