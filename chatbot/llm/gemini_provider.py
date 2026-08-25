import logging
import os

from google import genai
from dotenv import load_dotenv

from .base import LLMProvider

load_dotenv()

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"


class GeminiProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        return self._generate_with_fallback(prompt)

    def _generate_with_fallback(self, prompt: str) -> str:
        # List of models ordered by preference.
        # If the primary model fails, it falls back to the next alternative.
        # Every entry here was verified with a live generate_content() call
        # against this API key (models.list() alone isn't reliable -- it
        # listed several models, e.g. gemini-2.5-flash-lite and
        # gemini-2.5-pro, as supporting generateContent that 404 in practice
        # as "no longer available to new users"). Ordered so that if
        # gemini-2.5-flash's separate, tight free-tier quota (20/day) is
        # exhausted, the rest have their own independent quotas to try.
        models_fallback_matrix = [
            "gemini-2.5-flash",             # Primary Model
            "gemini-flash-latest",          # Fallback 1 (rolling alias, stays valid across model retirements)
            "gemini-flash-lite-latest",     # Fallback 2 (cheap/fast rolling alias)
            "gemini-3-flash-preview",       # Fallback 3
            "gemini-3.1-flash-lite",        # Fallback 4
            "gemini-3.5-flash",             # Fallback 5
            "gemini-3.5-flash-lite",        # Fallback 6
            "gemini-3.6-flash",             # Fallback 7
        ]

        last_exception = None

        for model_name in models_fallback_matrix:
            try:
                logger.info("Attempting prompt execution with model: %s", model_name)
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                # If successful, immediately return the text
                return response.text.strip()

            except Exception as error:
                logger.warning("Model %s failed, switching to next fallback: %s", model_name, error)
                last_exception = error
                continue  # Jump to the next iteration of the loop

        # If all models in the list fail, raise the last encountered error
        logger.error("All available fallback models have been exhausted.")
        raise last_exception

    def embed(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )
        return list(response.embeddings[0].values)
