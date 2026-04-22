from django.db import models
from django.contrib.auth.models import User
import uuid

class DocumentType(models.Model):
#  Tabble to categorize documents (e.g., Invoice, Contract, Report)
    type_name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    allowed_extensions = models.CharField(max_length=200, default='pdf,jpg,png,tiff')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.type_name

    class Meta:
        db_table = 'document_types'

class Document(models.Model):
  # Main table to store document metadata and track workflow status
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('in_workflow', 'In Workflow'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
        ('rejected', 'Rejected'),
    ]

    SOURCE_CHOICES = [
        ('manual', 'Manual Upload'),
        ('onedrive', 'OneDrive Document'),
    ]

    # Using UUID for primary key is safer for distributed systems
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_name = models.CharField(max_length=255)
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    submitted_date = models.DateTimeField(auto_now_add=True)
    current_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='uploaded'
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='manual'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )
    file_hash = models.CharField(max_length=64, unique=True)
    ai_summary = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.document_name

    class Meta:
        db_table = 'documents'
        ordering = ['-submitted_date']

class ManualUploadDocument(models.Model):
   # imported documents from manual uploads. 
   # This allows us to track the source and file details separately from OneDrive imports.
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='manual_upload'
    )
    file = models.FileField(upload_to='manual_uploads/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'manual_upload_documents'

class OneDriveDocument(models.Model):
    #imported documents from OneDrive. 
    # This allows us to track the source and sync status separately from manual uploads.
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='onedrive_doc'
    )
    one_drive_file_id = models.CharField(max_length=255)
    drive_url = models.URLField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'onedrive_documents'

class DocumentVersion(models.Model):
   # This table tracks different versions of a document
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.IntegerField(default=1)
    file = models.FileField(upload_to='versions/%Y/%m/')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    change_note = models.TextField(blank=True)

    class Meta:
        db_table = 'document_versions'
        ordering = ['-version_number']

class OneDriveSyncLog(models.Model):
   # This table logs the synchronization process with OneDrive, including successes and failures.
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
        ('processing', 'Processing'),
    ]

    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    records_processed = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    workflow_type = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'OneDrive_import_logs'
        ordering = ['-imported_at']