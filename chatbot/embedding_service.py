"""RAG plumbing for the chatbot: builds an embedding index over the content
that actually exists today (workflow definitions, document names, workflow
instance names) and retrieves the most relevant snippets for a question.

`access_flags` on each KnowledgeEmbedding row and `filter_by_access()` below
are the intended integration point for permission-aware retrieval once the
real permissions table is merged (per the architecture in the plan) -- until
then every row defaults to ["public"] and filter_by_access() is a no-op.
"""

import logging
import math

from analytics.models import Document, Workflow, WorkflowInstance

from .llm_service import LLMService
from .models import KnowledgeEmbedding

logger = logging.getLogger(__name__)

# Empirically, unrelated queries (e.g. "hello") score ~0.5-0.57 cosine
# similarity against this indexed corpus while genuine descriptive
# questions ("what does the X workflow involve") score ~0.7-0.8. This lets
# retrieve() be called unconditionally -- including for plain greetings --
# without injecting irrelevant context into the response prompt. May need
# retuning if the embedding backend changes, since different embedding
# models produce different score distributions.
MIN_RELEVANCE_SCORE = 0.6

# Embeddings always use Gemini, independent of whichever provider the user
# picked for chat generation. Two vectors are only comparable if the same
# model produced them, so retrieval must use whatever embedded the index
# (see reindex() below); it can't follow a per-message "gemini"/"ollama"
# generation-provider switch. Ollama is also not guaranteed to have an
# embedding model pulled locally the way it needs a chat model pulled.
EMBEDDING_PROVIDER = "gemini"


def _upsert(source_type, source_id, text, embedding, workflow_id=None, access_flags=None):
    KnowledgeEmbedding.objects.update_or_create(
        source_type=source_type,
        source_id=source_id,
        defaults={
            "text": text,
            "embedding": embedding,
            "workflow_id": workflow_id,
            "access_flags": access_flags or ["public"],
        },
    )


def reindex() -> int:
    """(Re)build the embedding index. When the real document-content/summary
    model merges, extend this to also embed it with the same
    access_flags/workflow linkage."""
    llm = LLMService(provider_override=EMBEDDING_PROVIDER)
    count = 0

    for workflow in Workflow.objects.all():
        text = f"Workflow: {workflow.name}\nDefinition: {workflow.definition}"
        embedding = llm.embed(text)
        _upsert("workflow", workflow.workflow_id, text, embedding, workflow_id=workflow.workflow_id)
        count += 1

    for document in Document.objects.all():
        text = f"Document: {document.document_name}"
        embedding = llm.embed(text)
        _upsert("document", document.document_id, text, embedding)
        count += 1

    for instance in WorkflowInstance.objects.all():
        text = f"Workflow instance: {instance.instance_name} (status: {instance.status})"
        embedding = llm.embed(text)
        _upsert("instance", instance.instance_id, text, embedding, workflow_id=instance.workflow_id)
        count += 1

    logger.info("Chatbot knowledge index rebuilt: %d entries", count)
    return count


def filter_by_access(rows, user_context=None):
    """Placeholder for permission-aware filtering -- currently allow-all.
    TODO once the permissions table is merged: resolve user_context's role
    and keep only rows whose access_flags intersect what that role may see."""
    return rows


def _cosine_similarity(vector_a, vector_b) -> float:
    dot = sum(x * y for x, y in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(x * x for x in vector_a))
    norm_b = math.sqrt(sum(y * y for y in vector_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve(query: str, top_n: int = 5, user_context=None) -> list[str]:
    """Embed the query, rank indexed rows by cosine similarity, apply the
    (currently no-op) access filter, and return the top N texts above the
    relevance threshold. RAG context is a nice-to-have enhancement, not a
    critical path, so any embedding failure (e.g. Gemini rate-limited at
    that moment) degrades to "no context" instead of breaking the whole
    chat response."""
    rows = list(KnowledgeEmbedding.objects.all())
    rows = filter_by_access(rows, user_context)
    if not rows:
        return []

    try:
        llm = LLMService(provider_override=EMBEDDING_PROVIDER)
        query_embedding = llm.embed(query)
    except Exception as error:
        logger.warning("RAG retrieval skipped, embedding the query failed: %s", error)
        return []

    scored = [(row, _cosine_similarity(query_embedding, row.embedding)) for row in rows]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    relevant = [row.text for row, score in scored[:top_n] if score >= MIN_RELEVANCE_SCORE]
    return relevant
