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


with open(r'./config.yaml') as file:
	locationMappings = yaml.load(file, Loader=yaml.FullLoader)


def is_running():
	return True, "is running"

health.add_check(is_running)

# Get a list of all the pod IPs periodically or whenenver a new pod appears it calls an api
@app.route('/api/fetachallpods', methods=['GET'])
def fetchAllPods():
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.set('0.0.0.0:3000', json.dumps({
        "isActive": True, 
        "cpu": [],
        "memory": [],
        "latency": [],
        "result": []
    }), ex=10)
    return jsonify({ "written" : list(r.scan_iter("*")) })
    # contexts, active_context = config.list_kube_config_contexts()
    # if not contexts:
    #     print("Cannot find any context in kube-config file.")
    #     return
    # contexts = [context['name'] for context in contexts]
    # active_index = contexts.index(active_context['name'])
    # cluster1, first_index = pick(contexts, title="Pick the first context",
    #                              default_index=active_index)
    # cluster2, _ = pick(contexts, title="Pick the second context",
    #                    default_index=first_index)

    # client1 = client.CoreV1Api(
    #     api_client=config.new_client_from_config(context=cluster1))
    # client2 = client.CoreV1Api(
    #     api_client=config.new_client_from_config(context=cluster2))

    # print("\nList of pods on %s:" % cluster1)
    # for i in client1.list_pod_for_all_namespaces().items:
    #     print("%s\t%s\t%s" %
    #           (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

    # print("\n\nList of pods on %s:" % cluster2)
    # for i in client2.list_pod_for_all_namespaces().items:
    #     print("%s\t%s\t%s" %
    #           (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


@app.route('/api/updatepods', methods=['GET'])
def updatePodsLocation():
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.set('0.0.0.0:3000', json.dumps({
        "isActive": True, 
        "cpu": [],
        "memory": [],
        "latency": [],
        "result": []
    }), ex=10)
    return jsonify({ "written" : list(r.scan_iter("*")) })


# Fetch all the IPs and call healthcheck on them to recieve aliveness, CPU, Memory
@app.route('/api/healthchecks', methods=['GET'])
def getHealthChecks():
    r = redis.Redis(host='localhost', port=6379, db=0)
    for key in r.scan_iter("*"):
        ipAddress = key.decode("utf-8")
        pastUsage = json.loads(r.get(ipAddress))
        print("ipAddressFetch", ipAddress, pastUsage)

        try:
            usageUpdateResponse = requests.get("http://" + ipAddress  + '/api/cpu/generateLoad?repeat=10', timeout=1).content        
            usageUpdate = dict(json.loads(usageUpdateResponse))
            print("New statistics", usageUpdate)

        except RequestException as e:
            print("Request didnt work, deleting the node from memory")
            r.delete(key, json.dumps(pastUsage))
            return jsonify( {"updatedIps": list(r.scan_iter("*")) })

        for metric in usageUpdate:
                if metric in pastUsage and len(pastUsage[metric]) > 10:
                    pastUsage[metric].pop(0)
                    pastUsage[metric].append(usageUpdate[metric])
                elif metric in pastUsage:
                    pastUsage[metric].append(usageUpdate[metric])
        print("Updated past object", pastUsage)
            
        r.set(key, json.dumps(pastUsage), ex=10)

    return jsonify( {"updatedIps": list(r.scan_iter("*")) })

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
	port = 3001
	if 'hasherHost' in os.environ:
		host = os.environ['hasherHost']
	if 'hasherPort' in os.environ:
		port = os.environ['hasherPort']
	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=True)