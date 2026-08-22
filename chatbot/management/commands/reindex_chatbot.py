from django.core.management.base import BaseCommand

from chatbot.embedding_service import reindex


class Command(BaseCommand):
    help = "Rebuild the chatbot's RAG knowledge index from workflows, documents, and workflow instances."

    def handle(self, *args, **options):
        count = reindex()
        self.stdout.write(self.style.SUCCESS(f"Indexed {count} entries."))
