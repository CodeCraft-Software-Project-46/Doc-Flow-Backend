# documents/admin.py
from django.contrib import admin
from .models import Document, DocumentType, ManualUploadDocument, CSVImportLog

# This makes your tables visible in the Django admin panel
admin.site.register(Document)
admin.site.register(DocumentType)
admin.site.register(ManualUploadDocument)
admin.site.register(CSVImportLog)