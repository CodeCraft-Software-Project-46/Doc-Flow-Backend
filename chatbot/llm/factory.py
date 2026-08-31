from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider

PROVIDER_NAMES = ("gemini", "ollama")


def get_provider(name: str, ollama_base_url: str | None = None, ollama_model: str | None = None) -> LLMProvider:
    if name == "gemini":
        return GeminiProvider()
    if name == "ollama":
        return OllamaProvider(base_url=ollama_base_url, model=ollama_model)
    raise ValueError(f"Unknown LLM provider: {name!r}. Available providers: {PROVIDER_NAMES}")
