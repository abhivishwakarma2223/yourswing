import requests
import json

def test_analysis(symbol="ADANIPORTS.NS"):
    url = f"http://localhost:8000/api/analysis/{symbol}"
    print(f"Testing Analysis for {symbol} at {url}...")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_analysis("ADANIPORTS.NS")
    test_analysis("RELIANCE.NS")
