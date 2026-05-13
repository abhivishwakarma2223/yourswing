import requests
import json

def test_analysis(symbol="NATIONALUM.NS"):
    url = f"http://localhost:8000/api/analysis/{symbol}"
    print(f"Testing Analysis for {symbol} at {url}...")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.statusCode if hasattr(response, 'statusCode') else response.status_code}")
        if response.status_code == 200:
            print("Success! JSON Response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_analysis()
