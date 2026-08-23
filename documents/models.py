from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone


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
        ('gdrive', 'Google Drive Document'),
    ]

    # Using UUID for primary key is safer for distributed systems
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_name = models.CharField(max_length=255)
    s3_url = models.URLField(max_length=500, blank=True, null=True)
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
   # This allows us to track the source and file details separately from GDrive imports.
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

class GoogleDriveDocument(models.Model):
    #imported documents from Google Drive. 
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='gdrive_doc'
    )
    gdrive_file_id = models.CharField(max_length=255)
    drive_url = models.URLField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'gdrive_documents'

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

class GoogleDriveSyncLog(models.Model):
   # This table logs the synchronization process with Google Drive, including successes and failures.
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
        db_table = 'gdrive_import_logs'
        ordering = ['-imported_at']

class GDriveFolderMapping(models.Model):
    # The name the user types in your React frontend (e.g., "Purchase Requests")
    folder_name = models.CharField(max_length=255, unique=True)
    
    # The actual ID Microsoft generates when your backend creates the folder
    gdrive_folder_id = models.CharField(max_length=255, null=True, blank=True) 
    
    # Matches the ID in your teammate's 'workflows_workflow' table
    workflow_id = models.CharField(max_length=255)
    
    # We store the name so your frontend can easily display it in a table 
    # without having to do complex database joins every time
    workflow_name = models.CharField(max_length=255) 
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.folder_name} mapped to {self.workflow_name}"

    class Meta:
        db_table = 'gdrive_folder_mappings'

class ExternalWorkflow(models.Model):
    """
    An unmanaged proxy model to read from Awishka's workflows_workflow table.
    Django will NOT try to run migrations on this table.
    """
    # Django automatically assumes there is an 'id' primary key, so we don't need to write it.
    name = models.CharField(max_length=255) 
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50) # Extremely useful for filtering
    
    class Meta:
        managed = False # CRITICAL: Keeps your migrations isolated from Awishka's
        db_table = 'workflows_workflow'


class ExternalWorkflowInstance(models.Model):
    """
    An unmanaged proxy model to insert live workflows into Awishka's engine.
    """
    # Awishka uses UUIDs for his instance IDs
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    document_name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    current_state = models.CharField(max_length=50)
    payload = models.TextField()
    runtime_state = models.TextField()
    
    # Notice this is a CharField because Awishka is using UUID strings for workflows!
    workflow_id = models.CharField(max_length=255) 

    started_at = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False # CRITICAL: Keeps your migrations safe
        db_table = 'workflows_workflowinstance'

class DocumentUploadLink(models.Model):
    """Stores secure, tokenized links for external document uploads."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Routing metadata embedded in the link
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    workflow_id = models.CharField(max_length=255)

    # Security controls
    is_revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        """Checks if the link is active and not expired."""
        if self.is_revoked:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True

    class Meta:
        db_table = 'document_upload_links'

