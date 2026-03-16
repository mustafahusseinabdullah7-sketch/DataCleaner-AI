import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("=== Testing OLD SDK (google.generativeai) ===")
try:
    import google.generativeai as old_genai
    old_genai.configure(api_key=api_key)
    model = old_genai.GenerativeModel('gemini-1.5-flash')
    resp = model.generate_content("Hello! Reply with OK.")
    print("SUCCESS: ", resp.text)
except Exception as e:
    print("ERROR OLD SDK with gemini-1.5-flash:", e)
    try:
        model = old_genai.GenerativeModel('gemini-2.0-flash')
        resp = model.generate_content("Hello! Reply with OK.")
        print("SUCCESS with 2.0: ", resp.text)
    except Exception as e2:
        print("ERROR OLD SDK with gemini-2.0-flash:", e2)

print("\n=== Testing NEW SDK (google-genai) ===")
try:
    from google import genai as new_genai
    client = new_genai.Client(api_key=api_key)
    
    # Try gemini-1.5-flash
    try:
        resp = client.models.generate_content(model='gemini-1.5-flash', contents="Hello! Reply with OK.")
        print("SUCCESS NEW SDK with 1.5:", resp.text)
    except Exception as e1:
        print("ERROR NEW SDK with 1.5:", e1)
        
    # Try gemini-2.0-flash
    try:
        resp = client.models.generate_content(model='gemini-2.0-flash', contents="Hello! Reply with OK.")
        print("SUCCESS NEW SDK with 2.0:", resp.text)
    except Exception as e2:
        print("ERROR NEW SDK with 2.0:", e2)
        
except Exception as e:
    print("ERROR setup NEW SDK:", e)
