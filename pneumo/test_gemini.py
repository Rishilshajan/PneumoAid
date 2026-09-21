import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print("API key loaded:", bool(api_key))

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY was not found in your .env file."
    )

client = genai.Client(api_key=api_key)

print("Testing Gemini...")

try:

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input="Explain pneumonia in one simple sentence."
    )

    print("\nGemini response:")
    print(interaction.output_text)

except Exception as e:

    print("\n========== GEMINI ERROR ==========")
    print("Error type:", type(e).__name__)
    print("Error:", str(e))
    print("==================================")