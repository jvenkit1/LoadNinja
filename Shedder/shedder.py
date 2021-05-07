from flask import Flask
from flask import jsonify
from flask import request
import yaml
import json
import os

import requests
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
@app.route('/api/updatepodslocation', methods=['GET'])
def updatePodsLocation():
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.set('0.0.0.0:3000', json.dumps({
        "isActive": True, 
        "cpu": [],
        "memory": [],
        "latency": []
    }))
    return jsonify({"written":True})
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



# Fetch all the IPs and call healthcheck on them to recieve aliveness, CPU, Memory
@app.route('/api/healthchecks', methods=['GET'])
def getHealthChecks():
    r = redis.Redis(host='localhost', port=6379, db=0)
    for key in r.scan_iter("*"):
        usageUpdate = requests.get("http://" + key.decode("utf-8")  + '/api/cpu/generateLoad?repeat=10').content
        print(json.loads(usageUpdate))



    return jsonify( {"written":json.loads(r.get('0.0.0.0:3000')) })
    

# Store which services are alive as well as the running average in local memory (move to redis) 


# When a new Request coming in
# Different categories of users * Different categories of APIs
# Check the threshold stored in redis, if above a certain threshold, respond with backoff 
# If below the threshold, forward the request to the server using kubernetes load balancer
# 
# 
# 





if __name__ == '__main__':
	host = "0.0.0.0"
	port = 3001
	if 'hasherHost' in os.environ:
		host = os.environ['hasherHost']
	if 'hasherPort' in os.environ:
		port = os.environ['hasherPort']
	app.add_url_rule("/health", "healthcheck", view_func = lambda: health.run())
	app.run(host=host, port=port, debug=True)