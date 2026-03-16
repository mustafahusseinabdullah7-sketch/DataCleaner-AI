"""Test the BYOK feature end-to-end: upload a file, then clean with API key"""
import requests
import io
import sys

BASE_URL = "http://127.0.0.1:8888"
API_KEY = sys.argv[1] if len(sys.argv) > 1 else ""

print("=== Testing Backend BYOK Feature ===")
print(f"API Key: {API_KEY[:10]}..." if API_KEY else "No API key provided (using .env key)")

# Small CSV test file in memory
csv_content = "Name,Age,City\nAhmed,25,Cairo\nAhmed,25,Cairo\nSara,30,Alex\n,,\n"
csv_bytes = csv_content.encode("utf-8")

# STEP 1: Upload
print("\n[1] Uploading test CSV...")
resp = requests.post(f"{BASE_URL}/upload",
                     files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
                     timeout=30)
print(f"    Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"    Error: {resp.text[:300]}")
    exit(1)

session_id = resp.json()["session_id"]
print(f"    Session ID: {session_id[:20]}...")

# STEP 2: Clean with BYOK
print(f"\n[2] Sending clean request...")
resp = requests.post(f"{BASE_URL}/clean",
                     data={
                         "session_id": session_id,
                         "user_request": "remove duplicate rows",
                         "gemini_api_key": API_KEY
                     },
                     timeout=90)
print(f"    Status: {resp.status_code}")
data = resp.json()
if resp.status_code == 200:
    print(f"    SUCCESS! Model: {data.get('model_used', 'unknown')}")
    print(f"    Rows: {data.get('rows_before')} -> {data.get('rows_after')}")
else:
    print(f"    Error: {data.get('detail', data)[:300]}")

print("\n=== Done ===")
