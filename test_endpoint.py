import requests
try:
    print("Testing /verify-key...")
    resp = requests.post("http://127.0.0.1:8000/verify-key", data={"gemini_api_key": "test"})
    print(f"Status: {resp.status_code}")
    print(f"Text: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
