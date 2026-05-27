from google import genai  #library for google gemini models
import os
from dotenv import load_dotenv
#LLM Adapter layer

#  Load the variables from .env
load_dotenv()

class GeminiProvider:                  
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        self.client = genai.Client(api_key=api_key) # Initialize the Gemini client with the API key

    def generate_with_fallback(self, prompt: str) -> str:
        # List of models ordered by preference.
        # If the primary model fails, it falls back to the next alternative.
        models_fallback_matrix = [
            "gemini-2.5-flash",             # Primary Model
            "gemini-1.5-flash-lite",        # Fallback 1 (Highly available stable model)
            "gemini-1.5-flash",             # Tier 3: Core stable legacy backup
            "gemini-2.0-flash",             # Tier 4: Highly cost-effective alternative general model
            "gemini-2.5-pro",               # Fallback 2 (Powerful pro model tier)
            "gemini-3-flash-preview",        # Fallback 3 (Experimental backup)
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite"
        ]
        
        last_exception = None

        for model_name in models_fallback_matrix:
            try:
                print(f"🤖 Attempting prompt execution with model: {model_name}")
                response = self.client.models.generate_content(
                    model=model_name,     
                    contents=prompt 
                )
                # If successful, immediately return the text
                return response.text.strip()
                
            except Exception as error:
                print(f"⚠️ Model {model_name} failed. Error: {error}")
                last_exception = error
                print("🔄 Switching to the next available fallback model...")
                continue # Jump to the next iteration of the loop
        
        # If all models in the list fail, raise the last encountered error
        print("❌ All available fallback models have been exhausted.")
        raise last_exception
        
class LLMService:
    def __init__(self):
        self.provider = GeminiProvider()  

    def generate(self, prompt):
        return self.provider.generate_with_fallback(prompt)