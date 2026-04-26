# documents/admin.py
from django.contrib import admin
from .models import (
    Document, 
    DocumentType, 
    ManualUploadDocument, 
    GoogleDriveDocument,  
    DocumentVersion, 
    GoogleDriveSyncLog,          
    GDriveFolderMapping,    
    ExternalWorkflow
)

# This makes your tables visible in the Django admin panel
admin.site.register(Document)
admin.site.register(DocumentType)
admin.site.register(ManualUploadDocument)
admin.site.register(GoogleDriveSyncLog)
admin.site.register(GDriveFolderMapping)
admin.site.register(ExternalWorkflow)   
admin.site.register(GoogleDriveDocument)
admin.site.register(DocumentVersion)