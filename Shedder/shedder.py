from flask import Flask
from flask import jsonify
from flask import request
import yaml
import json
import os

import requests
from requests.exceptions import RequestException
import redis

from kubernetes import client, config
from kubernetes.client import configuration
from pick import pick  # install pick using `pip install pick`


from healthcheck import HealthCheck, EnvironmentDump

app = Flask(__name__)
health = HealthCheck()
envdump = EnvironmentDump()

redisHost = "0.0.0.0"
redisPort = 6379
redisPassword = ''

REDIS_PREFIX = "cpu/"
SLIDING_WINDOW_SIZE = 10
SERVICE_PORT = ":3000"

with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)


def is_running():
	return True, "is running"

health.add_check(is_running)

# Creates a list of pods in redis at service startup
@app.route('/api/shed/createpodslist', methods=['GET'])
def createPodsList():
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    contexts, active_context = config.list_kube_config_contexts()
    if not contexts:
        print("Cannot find any context in kube-config file.")
        return
    print("Context", contexts, "Active context", active_context)

    contexts = [context['name'] for context in contexts]
    print("Context", contexts)

    active_index = contexts.index(active_context['name'])
    print("Active Index", active_index)

    cluster1, first_index = pick(contexts, title="Pick the first context",
                                 default_index=active_index)

    client1 = client.CoreV1Api(
        api_client=config.new_client_from_config(context=cluster1))

    print("\nList of pods on %s:" % cluster1)
    for i in client1.list_namespaced_pod(REDIS_PREFIX[:-1]).items:
        print("%s\t%s\t%s" %
              (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
        r.set(REDIS_PREFIX + i.status.pod_ip + SERVICE_PORT, json.dumps({
            "isActive": True, 
            "cpu": [],
            "memory": [],
            "latency": [],
            "result": []
        }))

    keyList = [ key.decode('UTF-8') for key in r.scan_iter(REDIS_PREFIX + "*") ]
    return jsonify({ "written" : keyList })


@app.route('/api/shed/updatepodslist', methods=['POST'])
def updatePodsList():
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    data = request.get_json()
    ip_addr = data["ip"]
    r.set(REDIS_PREFIX + ip_addr + SERVICE_PORT, json.dumps({
        "isActive": True, 
        "cpu": [],
        "memory": [],
        "latency": [],
        "result": []
    }))
    keyList = [ key.decode('UTF-8') for key in r.scan_iter(REDIS_PREFIX + "*") ]
    return jsonify({ "written" :  keyList})





# Empty the Redis cache
@app.route('/api/shed/deletepodslist', methods=['DELETE'])
def deletePodsList():
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    for key in r.scan_iter(REDIS_PREFIX + "*"):
        r.delete(key)
    keyList = [ key.decode('UTF-8') for key in r.scan_iter(REDIS_PREFIX + "*") ]
    return jsonify({ "written" :  keyList})





# Fetch all the IPs from Redis and call healthcheck on them to recieve aliveness, CPU, Memory
@app.route('/api/shed/healthchecks', methods=['GET'])
def getHealthChecks():
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    # Iterate through all keys with the REDIS_PREFIX
    for key in r.scan_iter(REDIS_PREFIX + "*"):
        # Key is returned in bytes, converting it into a string
        ipAddress = key.decode("utf-8")
        # Gets the value stored in redis for the particular key, converts it into a JSON object
        pastUsage = json.loads(r.get(ipAddress))
        print("ipAddressFetch", ipAddress[len(REDIS_PREFIX):], pastUsage)

        try:
            # Remove REDIS_PREFIX from key, send request to the resultant IP to fetch the health of the server
            # endPoint = "http://" + ipAddress[len(REDIS_PREFIX):]  + '/metrics'
            endPoint = "http://10.4.2.7:3000/metrics"
            print("Reaching out to " + endPoint)
            usageUpdateResponse = requests.get(endPoint, timeout=1).content
            print("Metadata", usageUpdateResponse)
            usageUpdate = dict(json.loads(usageUpdateResponse))
            print("New statistics", usageUpdate)

            for metric in usageUpdate:
                if metric in pastUsage and len(pastUsage[metric]) > SLIDING_WINDOW_SIZE:
                    pastUsage[metric].pop(0)
                    pastUsage[metric].append(usageUpdate[metric])
                elif metric in pastUsage:
                    pastUsage[metric].append(usageUpdate[metric])
            print("Updated past object", pastUsage)
                
            r.set(key, json.dumps(pastUsage))

        except RequestException as e:
            # If the request gives an error, delete key from Redis as the server is unresponsive
            print("Request didnt work, deleting the node from memory:", e)
            r.delete(key, json.dumps(pastUsage))

    keyList = [ key.decode('UTF-8') for key in r.scan_iter(REDIS_PREFIX + "*") ]
    return jsonify( {"updatedIps": keyList })



# When a new Request coming in
# Different categories of users * Different categories of APIs
# Check the threshold stored in redis, if above a certain threshold, respond with backoff 
# If below the threshold, forward the request to the server using kubernetes load balancer
# Fetch all the IPs and call healthcheck on them to recieve aliveness, CPU, Memory
@app.route('/api/cpu/<requestType>', methods=['GET'])
def requestForwarder(requestType):
    print(requestType)
    return jsonify( {"requestType": requestType })





if __name__ == '__main__':
	host = "0.0.0.0"
	port = 3004
	if 'shedderHost' in os.environ:
		host = os.environ['shedderHost']
	if 'shedderPort' in os.environ:
		port = os.environ['shedderPort']

    # Get Redis information
	if 'redisHost' in os.environ:
		redisHost = os.environ['redisHost']
	if 'redisPort' in os.environ:
		redisPort = os.environ['redisPort']
	if 'redisPassword' in os.environ:
		redisPassword = os.environ['redisPassword']


	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=True)