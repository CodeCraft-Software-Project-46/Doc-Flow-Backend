from google import genai  #library for google gemini models
import os
from dotenv import load_dotenv
#LLM Adapter layer

# 2. Load the variables from .env
load_dotenv()

class GeminiProvider:                  
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        self.client = genai.Client(api_key=api_key) # Initialize the Gemini client with the API key

    def generate(self, prompt):
        response = self.client.models.generate_content( #send the prompt to the Gemini model and get the response
            model="gemini-2.5-flash",     #gemini-3-flash-preview      gemini-2.5-flash
            contents=prompt
        )
        return response.text.strip()
        
class LLMService:
    def __init__(self):
        self.provider = GeminiProvider()  # later we can switch 

    def generate(self, prompt):
        return self.provider.generate(prompt)