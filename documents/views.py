import hashlib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentType, ManualUploadDocument, ExternalWorkflow, ExternalWorkflowInstance
from rest_framework.permissions import AllowAny
from .models import GDriveFolderMapping, ExternalWorkflow
from .gdrive_service import GDriveService
from rest_framework.permissions import AllowAny
from rest_framework import status, generics
from .serializers import DocumentTypeSerializer, DocumentSerializer
import json
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from .s3_service import S3Service
from .ai_service import DocumentAIService
  


class ManualUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        doc_type_id = request.data.get('document_type_id')
        workflow_id = request.data.get('workflow_id') # <-- NEW: The UI needs to send this!
        
        if not file_obj or not doc_type_id or not workflow_id:
            return Response({"error": "File, document_type_id, and workflow_id are required."}, status=400)

        # 1. Calculate SHA-256 Hash to prevent duplicates
        sha256_hash = hashlib.sha256()
        for chunk in file_obj.chunks():
            sha256_hash.update(chunk)
        file_hash = sha256_hash.hexdigest()

        # Reset file pointer after hashing
        file_obj.seek(0)

        # 2. Duplicate Check
        if Document.objects.filter(file_hash=file_hash).exists():
            return Response({"error": "This document has already been uploaded."}, status=409)

        # 3. Save Logic
        try:
            doc_type = DocumentType.objects.get(id=doc_type_id)
            
            # --- NEW: Spin up the Engines ---
            file_content = file_obj.read()
            mime_type = file_obj.content_type
            file_name = file_obj.name

            s3_service = S3Service()
            ai_service = DocumentAIService()

            # Upload to AWS S3 & Summarize
            s3_url = s3_service.upload_file_bytes(file_content, file_name, mime_type)
            summary_text = ai_service.generate_summary(file_content, mime_type)
            # --------------------------------

            # Create core Document
            new_doc = Document.objects.create(
                document_name=file_name,
                document_type=doc_type,
                source='manual',
                file_hash=file_hash,
                ai_summary=summary_text, # <-- Saved!
                s3_url=s3_url            # <-- Saved!
            )
            
            # Create Manual Metadata
            file_obj.seek(0) # Reset pointer again just in case Django's FileField needs it
            ManualUploadDocument.objects.create(
                document=new_doc,
                file=file_obj,
                original_filename=file_name,
                file_size=file_obj.size,
                mime_type=mime_type
            )

            # --- NEW: THE HANDSHAKE ---
            ExternalWorkflowInstance.objects.create(
                workflow_id=str(workflow_id),  
                document_name=new_doc.document_name,
                document_type=doc_type.type_name, 
                status='RUNNING', 
                current_state='Start',
                created_at=timezone.now(), 
                updated_at=timezone.now(), 
                started_at=timezone.now(), 
                payload=json.dumps({
                    "document_id": str(new_doc.id),
                    "source": "Manual Upload",
                    "ai_summary": summary_text
                }),
                runtime_state="{}"
            )
            # --------------------------
            
            return Response({
                "message": "Upload successful, secured in S3, and workflow triggered!", 
                "document_id": new_doc.id,
                "s3_url": s3_url
            }, status=201)
            
        except DocumentType.DoesNotExist:
            return Response({"error": "Invalid Document Type selected"}, status=400)
        except Exception as e:
            # Catching generic exceptions ensures a crashed S3 upload doesn't just return a blank 500 page
            return Response({"error": str(e)}, status=500)   

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
    """Handles creating folders in Google Drive and mapping them to workflows"""
    
    def get(self, request):
        """List all existing mappings for the frontend table"""
        mappings = GDriveFolderMapping.objects.all().values(
            'id', 'folder_name', 'workflow_name', 'is_active'
        )
        return Response(mappings, status=200)

    def post(self, request):
        """Create a new folder in Google Drive and map it"""
        folder_name = request.data.get('folder_name')
        workflow_id = request.data.get('workflow_id')
        workflow_name = request.data.get('workflow_name')

        if not folder_name or not workflow_id:
            return Response({"error": "Folder name and workflow are required"}, status=400)

        # 1. Call Google Drive API to physically create the folder
        try:
            service = GDriveService()
            gdrive_id = service.create_folder(folder_name)
        except Exception as e:
            return Response({"error": f"Failed to create folder in Google Drive: {str(e)}"}, status=500)

        # 2. Save the mapping in your AWS MySQL database
        mapping = GDriveFolderMapping.objects.create(
            folder_name=folder_name,
            gdrive_folder_id=gdrive_id,
            workflow_id=workflow_id,
            workflow_name=workflow_name
        )

        return Response({
            "message": "Folder created and mapped successfully!",
            "mapping_id": mapping.id
        }, status=201)
    
class CreateFolderMappingView(APIView):
    """
    API endpoint to dynamically create a Google Drive folder 
    and map it to a workflow in the database.
    """
    permission_classes = [AllowAny]
    def post(self, request):
        folder_name = request.data.get('folder_name')
        workflow_id = request.data.get('workflow_id')
        workflow_name = request.data.get('workflow_name', 'Unnamed Workflow')

        # Basic validation
        if not folder_name or not workflow_id:
            return Response(
                {"error": "Please provide both 'folder_name' and 'workflow_id'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. PASTE YOUR MASTER PARENT FOLDER ID HERE
        PARENT_FOLDER_ID = "1qWRHEans-FRu41gBtaKiP5E29kFk0nEX"

        try:
            # 2. Initialize Google Drive Engine
            drive_service = GDriveService()
            
            # 3. Ask Google to create the physical folder inside your Master folder
            gdrive_folder_id = drive_service.create_folder(
                folder_name=folder_name, 
                parent_folder_id=PARENT_FOLDER_ID
            )

            # 4. Save the new mapping to AWS MySQL
            mapping = GDriveFolderMapping.objects.create(
                folder_name=folder_name,
                gdrive_folder_id=gdrive_folder_id,
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                is_active=True
            )

            return Response({
                "message": f"Successfully created and mapped folder: {folder_name}",
                "gdrive_folder_id": gdrive_folder_id,
                "workflow_id": workflow_id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class DocumentTypeListCreateView(generics.ListCreateAPIView):
    """
    GET: Returns a list of all document types.
    POST: Creates a new document type.
    """
    permission_classes = [AllowAny]
    queryset = DocumentType.objects.all().order_by('-created_at')
    serializer_class = DocumentTypeSerializer

class DocumentListView(generics.ListAPIView):
    """
    GET: Returns a list of all processed documents (Manual & GDrive).
    """
    permission_classes = [AllowAny] 
    queryset = Document.objects.all().order_by('-submitted_date') # Newest files first
    serializer_class = DocumentSerializer

class DocumentTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]  # Disable authentication for this view
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer

@api_view(['GET'])
@permission_classes([AllowAny])
def get_upload_dropdowns(request):
    """
    Fetches the active Document Types and Workflows to populate the React frontend dropdowns.
    """
    try:
        # 1. Fetch Document Types (only the active ones)
        # We use .values() to only grab the ID and Name to keep the payload tiny and fast
        doc_types = DocumentType.objects.filter(is_active=True).values('id', 'type_name')
        
        # 2. Fetch Workflows from Awishka's table via your proxy model
        # Assuming his active workflows have a status like 'Published', 'Active', or similar. 
        # If he doesn't use status, just remove the .filter() and use .all()
        workflows = ExternalWorkflow.objects.all().values('id', 'name')
        
        return Response({
            "document_types": list(doc_types),
            "workflows": list(workflows)
        }, status=200)
        
    except Exception as e:
        return Response({"error": str(e)}, status=500)


