from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Common interface every LLM backend (cloud API or local) must implement,
    so the rest of the chatbot never needs to know which one is active."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return a natural-language completion for the given prompt."""
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for the given text."""
        raise NotImplementedError
