from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
import yaml
import os
import random
import string

app = Flask(__name__)
with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)

# app.config['MONGO_DBNAME'] = locationMappings["db"]["name"]
# app.config['MONGO_URI'] = 'mongodb://' + locationMappings["db"]["url"] + ':' + str(locationMappings["db"]["port"]) + '/'+ locationMappings["db"]["name"]

app.config['MONGO_DBNAME'] = os.environ["dbName"]
app.config['MONGO_URI'] = 'mongodb://' + os.environ["dbUrl"] + ':' + str(os.environ["dbPort"]) + '/'+ os.environ["dbName"]

mongo = PyMongo(app)
letters = string.ascii_lowercase

@app.route('/bulkRead', methods=['GET'])
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


@app.route('/_writeName', methods=['POST'])
def write_name():
	star = mongo.db.stars
	name = ''.join(random.choice(letters) for i in range(10))
	rank = random.randrange(1000)
	star.update({"name": name}, {"$set": {'rank': rank}}, upsert = True)
	return jsonify({'result' : 	star.find_one({"name": name})})


@app.route('/bulkWrite', methods=['POST'])
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
	host = os.environ['writerHost']
	port = os.environ['writerPort']
	app.run(host=host, port=port, debug=True)
	# app.run(host=locationMappings['writer']['url'], port=locationMappings['writer']['port'], debug=True)