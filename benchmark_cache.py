import time
import requests

URL = "http://127.0.0.1:8000/api/v1/revenue/trends"

times = []

print("Benchmarking Revenue Trends API...\n")

for i in range(10):
    try:
        start = time.perf_counter()

        response = requests.get(URL, timeout=10)

        end = time.perf_counter()

        elapsed = (end - start) * 1000

        print(f"Request {i+1}: {elapsed:.2f} ms")

        times.append(elapsed)

    except Exception as e:
        print(f"Request {i+1} failed: {e}")

if times:
    print(f"\nAverage Response Time: {sum(times)/len(times):.2f} ms")