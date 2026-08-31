from .llm.factory import PROVIDER_NAMES, get_provider
from .models import ChatbotConfig


class LLMService:
    """Resolves which LLMProvider to use (per-request override, else the
    admin-configured default) and delegates generate()/embed() to it."""

    def __init__(self, provider_override: str | None = None):
        config = ChatbotConfig.current()

        provider_name = provider_override if provider_override in PROVIDER_NAMES else config.active_provider

        self.provider_name = provider_name
        self.provider = get_provider(
            provider_name,
            ollama_base_url=config.ollama_base_url,
            ollama_model=config.ollama_model,
        )

    def generate(self, prompt: str) -> str:
        return self.provider.generate(prompt)

    def embed(self, text: str) -> list[float]:
        return self.provider.embed(text)
