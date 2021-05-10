import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer
import time
from collections import defaultdict
import random

START_TIME = default_timer()
NUM_REQUESTS = 50

OPERATIONS = {i: [] for i in range(NUM_REQUESTS)}


def fetch(session, csv, tries):
    base_url = "http://0.0.0.0:3004/api/cpu/hashFile?repeat=30"
    with session.get(base_url, headers = {"user-type": "user-free", "request-type": "priority-low"}) as response:
        data = response.text
        retryingFlag = 0
        if response.status_code == 429:
            print("Backing off request number ", csv, " for ", int(response.headers["Retry-After"]), " retry number ", tries + 1)
            retryingFlag = 1
            OPERATIONS[csv].append("BACKOFF" + str(tries))
            time.sleep((int(response.headers["Retry-After"]) * (2**(tries-1))) + random.randint(0, 10))
            data = fetch(session, csv, tries + 1)
        elif response.status_code != 200:
            print("FAILURE::{0} {1}".format(base_url, response.status_code))
        else:
            OPERATIONS[csv].append("SERVED" + str(tries))

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
            tasks = [
                loop.run_in_executor(
                    executor,
                    fetch,
                    *(session, csv, 0) # Allows us to pass in multiple arguments to `fetch`
                )
                for csv in range(NUM_REQUESTS)
            ]
            for response in await asyncio.gather(*tasks):
                pass

def main():
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(get_data_asynchronous())
    loop.run_until_complete(future)
    print(OPERATIONS)

main()