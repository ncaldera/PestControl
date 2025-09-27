import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ No GEMINI_API_KEY found in .env file")

genai.configure(api_key=api_key)

# Quick test
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content("Write a haiku about debugging code")

print("Gemini says:\n", response.text)