"""Test that the cleaning endpoint works with a specific model"""
import os
from dotenv import load_dotenv
from google import genai
import pandas as pd
import sys

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Use provided key from sys.argv if given
if len(sys.argv) > 1:
    api_key = sys.argv[1]

print(f"Using key: {api_key[:10]}...")

# Test model
model_to_test = "models/gemini-2.0-flash-lite"
print(f"\nTesting model: {model_to_test}")

client = genai.Client(api_key=api_key)

test_prompt = "Write a 1-line Python pandas code to remove duplicate rows from df."
try:
    response = client.models.generate_content(
        model=model_to_test,
        contents=test_prompt
    )
    print(f"\n✅ SUCCESS! Model works.")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"\n❌ FAILED with {model_to_test}: {e}")
    print("\nTrying gemini-2.0-flash...")
    try:
        response = client.models.generate_content(
            model="models/gemini-2.0-flash",
            contents=test_prompt
        )
        print(f"✅ SUCCESS with gemini-2.0-flash!")
        print(f"Response: {response.text[:200]}")
    except Exception as e2:
        print(f"❌ FAILED with gemini-2.0-flash: {e2}")
        print("\nTrying gemini-2.5-flash...")
        try:
            response = client.models.generate_content(
                model="models/gemini-2.5-flash",
                contents=test_prompt
            )
            print(f"✅ SUCCESS with gemini-2.5-flash!")
        except Exception as e3:
            print(f"❌ All models failed: {e3}")
