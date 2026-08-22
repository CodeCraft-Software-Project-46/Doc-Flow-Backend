import logging

import requests

from .base import LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
# Local CPU inference is far slower than a cloud API, especially once a
# prompt includes a full data payload (e.g. several workflows' worth of KPI
# fields) for the model to read and format -- 60s was cutting off real,
# still-in-progress generations, not just genuinely hung requests.
REQUEST_TIMEOUT_SECONDS = 180


class OllamaUnavailableError(RuntimeError):
    """Raised when the local Ollama server can't be reached at all (not
    running, wrong port, etc.) -- distinct from a normal exception so the
    view can give the user an actionable message instead of the generic
    catch-all fallback."""


class OllamaProvider(LLMProvider):
    """Talks to a local Ollama server. Kept behind the same LLMProvider
    interface as GeminiProvider so the rest of the chatbot can switch
    between them without any other code changes."""

    def __init__(self, base_url: str | None = None, model: str | None = None, embed_model: str | None = None):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.embed_model = embed_model or DEFAULT_EMBED_MODEL

    def generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()["response"].strip()
        except requests.RequestException as error:
            logger.error("Ollama generate() request failed (model=%s, url=%s): %s", self.model, self.base_url, error)
            raise OllamaUnavailableError(f"Local Ollama model is unreachable: {error}") from error

    def embed(self, text: str) -> list[float]:
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return list(response.json()["embedding"])
        except requests.RequestException as error:
            logger.error("Ollama embed() request failed (model=%s, url=%s): %s", self.embed_model, self.base_url, error)
            raise OllamaUnavailableError(f"Local Ollama embedding model is unreachable: {error}") from error
