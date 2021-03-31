from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
import yaml

app = Flask(__name__)
with open(r'./config.yaml') as file:
  locationMappings = yaml.load(file, Loader=yaml.FullLoader)


app.config['MONGO_DBNAME'] = locationMappings["db"]["name"]
app.config['MONGO_URI'] = 'mongodb://' + locationMappings["db"]["url"] + ':' + str(locationMappings["db"]["port"]) + '/'+ locationMappings["db"]["name"]

mongo = PyMongo(app)

@app.route('/bulkRead', methods=['GET'])
def get_all_stars():
  star = mongo.db.stars
  output = []
  for s in star.find():
    output.append({'name' : s['name'], 'updated' : s['updated']})
  return jsonify({'result' : output})

@app.route('/bulkWrite', methods=['POST'])
def add_star():
  star = mongo.db.stars
  name = request.args['name']
  times = request.args['times']
  for i in range(times):
  	star.update({"name": name}, {"$set": {'updated': i}}, upsert = True)

  s = star.find_one({'name' : name})
  output = {'name' : s['name'], 'updated' : s['updated']}
  return jsonify({'result' : output})

if __name__ == '__main__':
    app.run(host=locationMappings['summer']['url'], port=locationMappings['summer']['port'], debug=True)