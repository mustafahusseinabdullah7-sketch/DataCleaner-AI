"""Quick test to find available models for the API key in .env"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
print(f"Key (partial): {api_key[:15]}..." if api_key else "No API key found!")

# Test with user-supplied key from args
if len(sys.argv) > 1:
    api_key = sys.argv[1]
    print(f"Using provided key: {api_key[:15]}...")

from google import genai

client = genai.Client(api_key=api_key)

print("\n--- Available models ---")
for m in client.models.list():
    print(f"  {m.name}")

# Find flash models
print("\n--- Models with 'flash' ---")
for m in client.models.list():
    if "flash" in m.name.lower():
        print(f"  {m.name}")
