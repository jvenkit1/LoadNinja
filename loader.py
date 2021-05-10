import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer
import time
from collections import defaultdict
import random
import pickle


START_TIME = default_timer()
NUM_REQUESTS = 50

OPERATIONS = {}


def fetch(session, csv, userChoice, requestChoice, tries):
    base_url = "http://0.0.0.0:3004/api/cpu/hashFile?repeat=30"
    with session.get(base_url, headers = {"user-type": userChoice, "request-type": requestChoice}) as response:
        data = response.text
        retryingFlag = 0
        if response.status_code == 429:
            # sleepTime = random.randint(0, 
            #     int(min(
            #         int(50 + random.randint(0, 10)), 
            #         int((int(response.headers["Retry-After"]) * (2**(tries-1))) + random.randint(0, 10))
            #     ))
            # )
            temp = int(min(
                    int(50 + random.randint(0, 10)), 
                    int((int(response.headers["Retry-After"]) * (2**(tries-1))) + random.randint(0, 10))
                ))
            sleepTime = temp / (2 + random.randint(0, int(temp/2)))
            print("Backing off request number ", csv, " for ", sleepTime, " retry number ", tries + 1)
            retryingFlag = 1
            OPERATIONS[str(csv) + '/' + userChoice + '/' + requestChoice].append({"BACKOFF": default_timer() - START_TIME})
            time.sleep(sleepTime)
            data = fetch(session, csv, userChoice, requestChoice, tries + 1)
        elif response.status_code != 200:
            print("FAILURE::{0} {1}".format(base_url, response.status_code))
        else:
            OPERATIONS[str(csv) + '/' + userChoice + '/' + requestChoice].append({"SERVED": default_timer() - START_TIME})

        if not retryingFlag:
            elapsed = default_timer() - START_TIME
            time_completed_at = "{:5.2f}s".format(elapsed)
            print("Request: {0:<30} {1:>20}".format(csv, time_completed_at))

        return data

async def get_data_asynchronous():
    with ThreadPoolExecutor(max_workers=12) as executor:
        with requests.Session() as session:
            # Set any session parameters here before calling `fetch`
            loop = asyncio.get_event_loop()
            START_TIME = default_timer()
            tasks = []
            for csv in range(NUM_REQUESTS):
                userChoice = random.choice(["user-free", "user-paid"])
                requestChoice = random.choice(["priority-low", "priority-medium", "priority-high"])
                OPERATIONS[str(csv) + '/' + userChoice + '/' + requestChoice] = []
                tasks.append(loop.run_in_executor(executor, fetch, *(session, csv, userChoice, requestChoice, 0)))

            for response in await asyncio.gather(*tasks):
                pass

def main():
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(get_data_asynchronous())
    loop.run_until_complete(future)
    f = open("base+jitter+inverse.pkl","wb")
    pickle.dump(OPERATIONS, f)
    f.close()

main()