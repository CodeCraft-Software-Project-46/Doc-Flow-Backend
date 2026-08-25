from django.contrib import admin

from .models import ChatbotConfig, KnowledgeEmbedding


@admin.register(ChatbotConfig)
class ChatbotConfigAdmin(admin.ModelAdmin):
    list_display = ("active_provider", "ollama_model", "ollama_base_url", "updated_at")


@admin.register(KnowledgeEmbedding)
class KnowledgeEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("source_type", "source_id", "workflow_id", "access_flags", "updated_at")
    list_filter = ("source_type",)
    search_fields = ("text",)
