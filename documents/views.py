import hashlib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentType, ManualUploadDocument
from rest_framework.permissions import AllowAny
from .models import OneDriveFolderMapping, ExternalWorkflow
from .onedrive_service import OneDriveService
from rest_framework.permissions import AllowAny

class ManualUploadView(APIView): # This view handles manual document uploads, ensuring no duplicates and proper metadata storage
    parser_classes = (MultiPartParser, FormParser) # Allow handling of file uploads and form data
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs): #triggered when a POST request is made to this endpoint
        file_obj = request.FILES.get('file') # Get the uploaded file from the request
        doc_type_id = request.data.get('document_type_id') # Get the document type ID from the form data
        
        if not file_obj:
            return Response({"error": "No file provided"}, status=400)

        # 1. Calculate SHA-256 Hash to prevent duplicates
        sha256_hash = hashlib.sha256()
        for chunk in file_obj.chunks():
            sha256_hash.update(chunk)
        file_hash = sha256_hash.hexdigest()

        # Reset file pointer after hashing so it can be saved properly
        file_obj.seek(0)

        # 2. Duplicate Check
        if Document.objects.filter(file_hash=file_hash).exists():
            return Response({"error": "This document has already been uploaded."}, status=409)

        # 3. Save Logic
        try:
            doc_type = DocumentType.objects.get(id=doc_type_id)
            
            # Create core Document
            new_doc = Document.objects.create(
                document_name=file_obj.name,
                document_type=doc_type,
                source='manual',
                file_hash=file_hash
            )
            
            # Create Manual Metadata
            ManualUploadDocument.objects.create(
                document=new_doc,
                file=file_obj,
                original_filename=file_obj.name,
                file_size=file_obj.size,
                mime_type=file_obj.content_type
            )
            
            return Response({
                "message": "Upload successful", 
                "document_id": new_doc.id
            }, status=201)
            
        except DocumentType.DoesNotExist:
            return Response({"error": "Invalid Document Type selected"}, status=400)
        


class WorkflowDropdownListView(APIView):
    permission_classes = [AllowAny]
    """Fetches available workflows from the AWS database for the frontend dropdown"""
    def get(self, request):
        try:
            # Query the unmanaged table. 
            # Note: You might need to check with Awishka to see what exact string 
            # they use for active workflows (e.g., 'active', 'published', 'running').
            # I am assuming 'active' here.
            active_workflows = ExternalWorkflow.objects.filter(
                status='active' 
            ).values('id', 'name', 'description')
            
            return Response(active_workflows, status=200)
            
        except Exception as e:
            return Response({"error": f"Failed to fetch workflows: {str(e)}"}, status=500)
        
class FolderMappingView(APIView):
    permission_classes = [AllowAny]
    """Handles creating folders in OneDrive and mapping them to workflows"""
    
    def get(self, request):
        """List all existing mappings for the frontend table"""
        mappings = OneDriveFolderMapping.objects.all().values(
            'id', 'folder_name', 'workflow_name', 'is_active'
        )
        return Response(mappings, status=200)

    def post(self, request):
        """Create a new folder in OneDrive and map it"""
        folder_name = request.data.get('folder_name')
        workflow_id = request.data.get('workflow_id')
        workflow_name = request.data.get('workflow_name')

        if not folder_name or not workflow_id:
            return Response({"error": "Folder name and workflow are required"}, status=400)

        # 1. Call Microsoft Graph API to physically create the folder
        try:
            service = OneDriveService()
            onedrive_id = service.create_folder(folder_name)
        except Exception as e:
            return Response({"error": f"Failed to create folder in Microsoft: {str(e)}"}, status=500)

        # 2. Save the mapping in your AWS MySQL database
        mapping = OneDriveFolderMapping.objects.create(
            folder_name=folder_name,
            onedrive_folder_id=onedrive_id,
            workflow_id=workflow_id,
            workflow_name=workflow_name
        )

        return Response({
            "message": "Folder created and mapped successfully!",
            "mapping_id": mapping.id
        }, status=201)