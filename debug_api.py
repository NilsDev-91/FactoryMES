import requests
import json

try:
    r = requests.get("http://localhost:8000/orders")
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print(e)
