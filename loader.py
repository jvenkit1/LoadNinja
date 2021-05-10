import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer

START_TIME = default_timer()

def fetch(session, csv):
    base_url = "http://0.0.0.0:3004/api/cpu/hashFile?repeat=10"
    with session.get(base_url, headers = {"user-type": "user-free", "request-type": "priority-low"}) as response:
        data = response.text
        retryingFlag = 0
        if response.status_code == 429:
            retryingFlag = 1
            data = fetch(session, csv)
        elif response.status_code != 200:
            print("FAILURE::{0} {1}".format(base_url, response.status_code))

        if not retryingFlag:
            elapsed = default_timer() - START_TIME
            time_completed_at = "{:5.2f}s".format(elapsed)
            print("Request: {0:<30} {1:>20}".format(csv, time_completed_at))

        return data

async def get_data_asynchronous():
    with ThreadPoolExecutor(max_workers=60) as executor:
        with requests.Session() as session:
            # Set any session parameters here before calling `fetch`
            loop = asyncio.get_event_loop()
            START_TIME = default_timer()
            tasks = [
                loop.run_in_executor(
                    executor,
                    fetch,
                    *(session, csv) # Allows us to pass in multiple arguments to `fetch`
                )
                for csv in range(100)
            ]
            for response in await asyncio.gather(*tasks):
                pass

def main():
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(get_data_asynchronous())
    loop.run_until_complete(future)

main()