---
title: "Optimal Load Shedding Strategies for a Chaotic System"
author:
  - Jairam Venkitachalam <jv1589@nyu.edu>
  - Vidit Bhargava <vvb238@nyu.edu>
---

For our Big Data and Machine Learning final project we develop a priority based load shedding mechanism to manage performance under peak loads, for a tiered microservice system. We validate our approach by injecting failures into the system using a chaos engineering tool and measuring performance and availability.


# Motivation

Made popular by Netflix, [Chaos Engineering](https://principlesofchaos.org/) is a discipline that helps developers build resilient applications. As chaos is introduced in a system, it overloads the functioning servers causing them to spend increasing amounts of their time context switching and become too slow to be useful. This degrades the throughput of the entire system. Thus, we need to put measures in place to ensure a smooth end-user experience. One of the major ways to handle such stress is [load shedding](https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/) which involves shedding excess load and maintaining predictable, consistent performance in the face of overload.
 However, rejecting requests once the servers are overloaded can hinder the user experience.  We need to throttle traffic based on [priority](https://netflixtechblog.com/keeping-netflix-reliable-using-prioritized-load-shedding-6cc827b02f94) which can be calculated using various strategies, a few of which we explore in our proposed solution. 


# Proposed Solution

We consider a basic multi-tiered microservice-based system where the user can issue HTTP requests to the different microservices. Our baseline metrics are collected under network traffic, where the system utilization is around 50%. 

To understand our solution, we must gloss over the following headings:

## Assumptions:

Following are the points we assume about the problem statement and the system itself:<br>
1. We have non-byzantine clients: <br>
  a. These clients do not cause a Denial of Service on the system. <br>
  b. When provided with a backoff time, they respond with another HTTP request only after the backoff time has expired. <br>
  c. Clients provide correct information about the system. <br>
3. Load Shedding strategies have a minimal overhead on the system: <br>
  a. They do not cause latencies when the overall load is minimal.<br>

## Methodology:

We iteratively design the system using the following strategy:
1. We first analyze the performance metrics of our system under normal load and a heavy load to obtain a benchmark.
2. Inject chaos into the system and obtain relevant performance metrics.
3. Design load shedding strategies to improve performance and availability.
4. Measure the performance of these strategies under various kinds of chaos(network delays, limited replicas, etc).

## Strategies:

We intend to implement the following types of strategies:
1. No Strategy: This is a barebones system, used to obtain a baseline. We perform no admission control and have no defined behavior for concurrent user requests.
2. Naive Rate Limiting: We perform rate-limiting with randomly assigned backoffs.
3. Priority-based Rate Limiting: We first categorize the user requests into different tiers based on their priority and perform per category rate limiting. This way, the backoff period for a request with higher priority will be less than the backoff for a lower priority request.


The priority is defined by the following parameters:
1. User Based: We categorize the users into different buckets based on their tier and usage pattern. Example: An example category could be free vs paid users.
2. Service Based: Certain applications have a higher priority/requirement for faster response compared to other applications. Example: Creating a new user has a lower priority compared to performing a transaction in a banking environment.

Based on this priority, we assign backoffs to requests. The intuition here is that users
with higher priority will get lower average response times. 


We intend to experiment with the following types of backoffs:
1. Random Backoff: Each request is assigned a backoff time based on a randomly generated value. The random value range is dependent on the priority of the request.
2. Exponential Backoff: The backoff period for each request will increase exponentially. Our initial belief is that this approach will not scale efficiently with an increase in user requests.


## Infrastructure:

We will host our system on a Kubernetes cluster and will use either Cloudlab or GCP for this(depending on feasibility). 

## Quantifying Progress and Evaluation Strategy:

A successful algorithm in this case will adhere to the contract of providing lower average latencies to higher priority requests.

That is, since we have different categories of user requests, we measure a successful algorithm by the fact that the higher priority requests face the least amount of delay even under peak loads. Thus, while providing comparable average response times to a vanilla system, our algorithm must ensure that the higher priority requests have minimal average response times.

## End Goal:

The end product is a set of working and viable load shedding policies that are able to effectively manage the load to the different services while maintaining availability and performance.



# Timeline

* Checkin I (03/30): Have a sample infrastructure up and running, with a few sample microservices which serve clients as well as communicate with each other and a load balancer that directs client requests to the specific service. We perform load testing on this system and obtain baseline information on metrics such as performance, throughput, response times. We use the tool Vegeta for this load testing activity.

* Checkin II (04/20): A mechanism to track the path of requests (jaeger), introduce chaos in the system (chaosmonkey). Set up evaluation mechanisms to quantify hindrance to user experience and a simple priority assigner in the load balancer

* Final Handin (05/11): We will have the different strategies mentioned in the proposed solution implemented in the load balancer as well as evaluation of different strategies based on the average latency and critical request timings. Moreover, we would have explored different throttling levels like individual service and global as well as progressive load shedding (higher throttling rates based on the intensity of load).


# Resources

https://dl.acm.org/doi/10.1145/3267809.3267823

https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/

https://netflixtechblog.com/keeping-netflix-reliable-using-prioritized-load-shedding-6cc827b02f94


