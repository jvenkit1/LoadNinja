# load-ninja
Designing Load shedding policies in a chaotic environment


## Description:

CPU_Service: Hasher - 3000
DB_Service : Writer - 3001
Memory_Service: Summer - 3002


Shedder - LB (Request forwarder) - 3004

## Dependencies:

CPU_Service: NONE
DB_Service : Mongo
Memory_Service: DB Service

Shedder: Redis


## Deploying services:

### CPU:
```
helm install cpu cpu_service -n cpu
```

### Memory:
```
helm install memory memory_service -n memory
```

### DB:
```
helm install db db_service -n db
```

### Redis:
```
helm install redis bitnami/redis --set auth.enabled=false
```

### MongoDB:
```
helm install mongo bitnami/mongodb --set resources.limits.cpu=200m --set resources.limits.memory=500m --set resources.requests.cpu=200m --set resources.requests.memory=500m
```
