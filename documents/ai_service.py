import os
from google import genai
from google.genai import types

class DocumentAIService:
    def __init__(self):
        # Initialize using the new Client architecture
        api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        
        # Using your high-quota model!
        self.model = 'gemini-2.5-flash-lite'

    def generate_summary(self, file_content_bytes, mime_type):
        """
        Takes the raw binary file and its format, and asks the AI to summarize it.
        """
        try:
            print(f"Sending document to AI (Type: {mime_type})...")
            
            prompt = """
            You are an enterprise document analysis AI. 
            Please review the attached document and provide a concise, 
            professional summary (3-4 sentences max) of its contents. 
            Identify the core purpose of the document.
            """
            
            # The new SDK syntax for passing binary files
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=file_content_bytes, mime_type=mime_type),
                    prompt
                ]
            )
            
            return response.text
            
        except Exception as e:
            print(f"AI Summarization failed: {str(e)}")
            return "AI Summary unavailable at this time."