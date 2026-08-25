from django.db import models


class ChatbotConfig(models.Model):
    """Singleton config row (same pattern as analytics.BottleneckScoreWeights /
    working_hours.WorkingHoursConfig) holding which LLM backend the chatbot
    uses by default. A request can still override it per-message via the
    `provider` field on ChatBotView.post."""

    PROVIDER_CHOICES = [
        ("gemini", "gemini"),
        ("ollama", "ollama"),
    ]

    active_provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="gemini")
    ollama_model = models.CharField(max_length=100, default="llama3")
    ollama_base_url = models.CharField(max_length=255, default="http://localhost:11434")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chatbot_config"

    def __str__(self):
        return f"Chatbot config (active_provider={self.active_provider})"

    @classmethod
    def current(cls):
        """Latest configured row, or the gemini-default in-memory instance if none has been saved yet."""
        return cls.objects.order_by("-updated_at").first() or cls()


class KnowledgeEmbedding(models.Model):
    """One embedded, retrievable chunk of workflow/document/instance text for
    the chatbot's RAG lookup. `access_flags` is a placeholder hook for
    permission-aware filtering: it defaults to ["public"] (visible to
    everyone) until the real permissions table is merged and
    chatbot.embedding_service.filter_by_access() is wired up to check it
    against the requesting user's role."""

    SOURCE_TYPE_CHOICES = [
        ("workflow", "workflow"),
        ("document", "document"),
        ("instance", "instance"),
    ]

    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES)
    source_id = models.IntegerField()
    workflow_id = models.IntegerField(null=True, blank=True)
    text = models.TextField()
    embedding = models.JSONField()
    access_flags = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chatbot_knowledge_embedding"
        constraints = [
            models.UniqueConstraint(fields=["source_type", "source_id"], name="unique_chatbot_embedding_source")
        ]

    def __str__(self):
        return f"{self.source_type}#{self.source_id}"
