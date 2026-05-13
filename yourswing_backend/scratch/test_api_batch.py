import requests
import json

url = "http://localhost:8000/api/prices/batch"
symbols = ["RELIANCE.NS", "TCS.NS"]
print(f"Calling {url} with {symbols}")
try:
    response = requests.post(url, json=symbols)
    print(f"Status Code: {response.statusCode if hasattr(response, 'statusCode') else response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
