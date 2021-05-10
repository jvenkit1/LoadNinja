from flask import Flask
from flask import jsonify
from flask import request
from flask import Response
import yaml
import json
import os
import socket
import sys

import requests
from requests.exceptions import RequestException
import redis

from kubernetes import client, config
from kubernetes.client import configuration
from pick import pick  # install pick using `pip install pick`

import backoff

from healthcheck import HealthCheck, EnvironmentDump
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)
health = HealthCheck()
envdump = EnvironmentDump()

redisHost = "0.0.0.0"
redisPort = 6379
redisPassword = ''

SLIDING_WINDOW_SIZE = 10
SHEDDER_PORT = 3004
SERVICE_PORT = 3000
SERVICE_TYPE = "cpu"
LABEL_SELECTOR = "cpu-cpu-service"
SERVICE_HOST = "0.0.0.0"


def is_running():
	return True, "is running"
health.add_check(is_running)



# Creates a list of pods in redis at service startup
@app.route('/api/shed/createpodslist', methods=['GET'])
def createPodsList():
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    # contexts, active_context = config.list_kube_config_contexts()
    # if not contexts:
    #     print("Cannot find any context in kube-config file.")
    #     return
    # # print("Context", contexts, "Active context", active_context)

    # contexts = [context['name'] for context in contexts]
    # # print("Context", contexts)

    # active_index = contexts.index(active_context['name'])
    # # print("Active Index", active_index)

    # cluster1, first_index = pick(contexts, title="Pick the first context",default_index=active_index)
    # client1 = client.CoreV1Api(api_client=config.new_client_from_config(context=cluster1))

    config.load_incluster_config()
    client1 = client.CoreV1Api()

    for i in client1.list_namespaced_pod(SERVICE_TYPE, label_selector = "app="+LABEL_SELECTOR).items:
        print("%s\t%s\t%s" %
              (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
        r.set(SERVICE_TYPE + '/' + i.status.pod_ip + ":" + str(SERVICE_PORT), json.dumps({
            # "isActive": True, 
            "cpu": [],
            "memory": [],
            "latency": [],
            "result": []
        }), nx=True)
    keyList = [ key.decode('UTF-8') for key in r.scan_iter(SERVICE_TYPE + '/' + "*") ]
    return jsonify({ "written" : keyList })



# Called when a new pod is instantiated, this adds the pod to Redis pod list
@app.route('/api/shed/updatepodslist', methods=['POST'])
def updatePodsList():
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    # print(request.form)
    data = request.form
    # data = json.loads(data)
    ipAddress = data["ip"]
    # print(ipAddress)
    r.set(SERVICE_TYPE + '/' + ipAddress + ":" + str(SERVICE_PORT), json.dumps({
        # "isActive": True, 
        "cpu": [],
        "memory": [],
        "latency": [],
        "result": []
    }), nx=True)
    keyList = [ key.decode('UTF-8') for key in r.scan_iter(SERVICE_TYPE + '/' + "*") ]
    return jsonify({ "written" :  keyList})



# Empty the Redis cache
@app.route('/api/shed/deletepodslist', methods=['DELETE'])
def deletePodsList():
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    for key in r.scan_iter(SERVICE_TYPE + '/' + "*"):
        r.delete(key)
    keyList = [ key.decode('UTF-8') for key in r.scan_iter(SERVICE_TYPE + '/' + "*") ]
    return jsonify({ "written" :  keyList})



@app.route('/api/shed/getpodslist', methods=['GET'])
def getPodsList():
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    podsInformation = []
    for key in r.scan_iter("*"):
        # Key is returned in bytes, converting it into a string
        ipAddress = key.decode("utf-8")
        # Gets the value stored in redis for the particular key, converts it into a JSON object
        pastUsage = json.loads(r.get(ipAddress))
        podsInformation.append({ipAddress: pastUsage})
        print("Pods Information", ipAddress, pastUsage)

    return jsonify({ "existing" :  podsInformation})


# Fetch all the IPs from Redis and call healthcheck on them to recieve aliveness, CPU, Memory
@app.route('/api/shed/healthchecks', methods=['GET'])
def getHealthChecks():
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    # Iterate through all keys with the REDIS_PREFIX
    for key in r.scan_iter(SERVICE_TYPE + '/' + "*"):
        # Key is returned in bytes, converting it into a string
        ipAddress = key.decode("utf-8")
        # Gets the value stored in redis for the particular key, converts it into a JSON object
        pastUsage = json.loads(r.get(ipAddress))
        print("ipAddressFetch", ipAddress[len(SERVICE_TYPE + '/'):], pastUsage, file=sys.stdout)

        try:
            # Remove REDIS_PREFIX from key, send request to the resultant IP to fetch the health of the server
            endPoint = "http://" + ipAddress[len(SERVICE_TYPE + '/'):]  + '/internal/metrics'
            endPoint = endPoint.replace(" ", "")
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
            print("Updated past object", pastUsage, file=sys.stdout)
                
            r.set(key, json.dumps(pastUsage))

        except RequestException as e:
            # If the request gives an error, delete key from Redis as the server is unresponsive
            print("Request didnt work, deleting the node from memory:", e, file=sys.stdout)
            r.delete(key, json.dumps(pastUsage))

    keyList = [ key.decode('UTF-8') for key in r.scan_iter(SERVICE_TYPE + '/' + "*") ]
    return jsonify( {"updatedIps": keyList })




# Different categories of users * Different categories of APIs
# Check the threshold stored statitically with the average values of metrics stored in redis 
# Respnd with corresponding maximum backoff
def getClusterBackoff(userType, requestType):
    r = redis.Redis(host=redisHost, port=redisPort, password=redisPassword, db=0)
    
    backoffValue = 0
    for key in r.scan_iter(SERVICE_TYPE + '/' + "*"):
        # Key is returned in bytes, converting it into a string
        ipAddress = key.decode("utf-8")
        # Gets the value stored in redis for the particular key, converts it into a JSON object
        pastUsage = json.loads(r.get(ipAddress))
        
        for key in pastUsage:
            # Calculating the average of the values, if no values exist return 0
            # print(pastUsage[key], key)
            averageMetric = sum(pastUsage[key])/len(pastUsage[key]) if len(pastUsage[key]) > 0 else 0

            if key not in backoff.BACKOFF_CONFIG[userType][requestType]:
                continue
            # Finding the index between which the averageMetric exists
            thresholdValues = backoff.BACKOFF_CONFIG[userType][requestType][key]
            index = 0
            while index < len(thresholdValues[0]):
                if index == len(thresholdValues[0]) - 1:
                    backoffValue = max(backoffValue, thresholdValues[1][index])
                elif thresholdValues[0][index] <= averageMetric < thresholdValues[0][index+1]:
                    backoffValue = max(backoffValue, thresholdValues[1][index])
                    break
                index += 1

    return backoffValue



# Sends a proxy request to the actual server
def _proxy(*args, **kwargs):
    # https://flask.palletsprojects.com/en/1.1.x/api/#flask.Request

    print("Path - {} \n FullPath - {}\n URL - {}\n BaseURL - {}\n ScriptRoot - {}\n URLRoot-{}\n".format(request.path, request.full_path, request.url, request.base_url, request.script_root, request.url_root))

    url = "http://" + SERVICE_HOST + ":" + str(SERVICE_PORT) + request.full_path.replace(SERVICE_TYPE, "_" + SERVICE_TYPE)
    print(url)

    resp = requests.request(
        method=request.method,
        url = url.replace(" ", ""),
        # url=request.url.replace(SERVICE_TYPE, "_" + SERVICE_TYPE).replace(str(SHEDDER_PORT), str(SERVICE_PORT)),
        headers={key: value for (key, value) in request.headers if key != 'Host'},
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False)

    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items()
               if name.lower() not in excluded_headers]

    response = Response(resp.content, resp.status_code, headers)
    return response


@app.route('/api/cpu/<requestType>', methods=['GET', 'POST'])
def requestForwarder(requestType):
    if "user-type" not in request.headers or "request-type" not in request.headers:
        return Response(json.dumps({"error": "Required fields not specified"}), status=400, mimetype='application/json')
    backoff = getClusterBackoff(request.headers["user-type"], request.headers["request-type"])
    if backoff > 0:
        print("Backing off the request")
        return Response(json.dumps({"error": "Server is overloaded, please try later"}), status=429, headers={"Retry-After": backoff}, mimetype='application/json')
    else:
        print("No backoff, forwarding the request")
        return _proxy(request)





if __name__ == '__main__':
	host = "0.0.0.0"
	port = SHEDDER_PORT
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

	if 'servicePort' in os.environ:
		SERVICE_PORT = os.environ['servicePort']
	if 'serviceType' in os.environ:
		SERVICE_TYPE = os.environ['serviceType']
	if 'serviceHost' in os.environ:
		SERVICE_HOST = os.environ['serviceHost']
	if 'labelSelector' in os.environ:
		LABEL_SELECTOR = os.environ['labelSelector']

	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=False, threaded=True)