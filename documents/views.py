import hashlib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentType, ManualUploadDocument, ExternalWorkflow, ExternalWorkflowInstance
from .models import GDriveFolderMapping, ExternalWorkflow
from .gdrive_service import GDriveService
from rest_framework import status, generics
from .serializers import DocumentTypeSerializer, DocumentSerializer
import json
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from .s3_service import S3Service
from .ai_service import DocumentAIService

import datetime
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import DocumentUploadLink

  

class ManualUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file') # File we upload from the frontend.
        doc_type_id = request.data.get('document_type_id') # The selected document type ID from the dropdown.
        workflow_id = request.data.get('workflow_id') # The selected workflow ID from the dropdown.

        if not file_obj or not doc_type_id or not workflow_id:
            return Response({"error": "File, document_type_id, and workflow_id are required."}, status=400)

        # 1. Fetch Document Type & Perform Strict File Validation
        try:
            doc_type = DocumentType.objects.get(id=doc_type_id) 
        except DocumentType.DoesNotExist:
            return Response({"error": "Invalid Document Type selected"}, status=400)

        file_ext = file_obj.name.split('.')[-1].lower() # Get file extension and normalize to lowercase
        allowed_exts = [ext.strip().lower() for ext in doc_type.allowed_extensions.split(',')] 
        
        if file_ext not in allowed_exts:
            return Response({
                "error": f"Invalid file type. Allowed formats for {doc_type.type_name} are: {doc_type.allowed_extensions.upper()}"
            }, status=400)

        # 2. Calculate SHA-256 Hash to prevent duplicates
        sha256_hash = hashlib.sha256()
        for chunk in file_obj.chunks():
            sha256_hash.update(chunk)
        file_hash = sha256_hash.hexdigest()

        # Reset file pointer after hashing
        file_obj.seek(0)

        # 3. Duplicate Check. Compare Hash against existing document hashes in the database.
        if Document.objects.filter(file_hash=file_hash).exists():
            return Response({"error": "This document has already been uploaded."}, status=409)

        # 4. Save Logic, S3 Upload, AI Summary, and Workflow Trigger
        try:
            # Spin up the Engines
            file_content = file_obj.read()
            mime_type = file_obj.content_type
            file_name = file_obj.name

            s3_service = S3Service() 
            ai_service = DocumentAIService()

            # Upload to AWS S3 & Summarize
            s3_url = s3_service.upload_file_bytes(file_content, file_name, mime_type)
            summary_text = ai_service.generate_summary(file_content, mime_type)

            # Create row in Document table
            new_doc = Document.objects.create(
                document_name=file_name,
                document_type=doc_type,
                source='manual',
                file_hash=file_hash,
                ai_summary=summary_text, 
                s3_url=s3_url            
            )
            
            # Create Manual upload Metadata
            file_obj.seek(0) # Reset pointer again
            ManualUploadDocument.objects.create(
                document=new_doc,
                file=file_obj,
                original_filename=file_name,
                file_size=file_obj.size,
                mime_type=mime_type
            )

            # Trigger the workflow by creating a new WorkflowInstance row in AWS MySQL
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
            
            return Response({
                "message": "Upload successful, secured in S3, and workflow triggered!", 
                "document_id": new_doc.id,
                "s3_url": s3_url
            }, status=201)
            
        except Exception as e:
            # Catching generic exceptions ensures a crashed S3 upload doesn't just return a blank 500 page
            return Response({"error": str(e)}, status=500)
        
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
        # Extract folder name and workflow details from the request
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

            # 4. Save the new mapping to AWS MySQL GDriveFolderMapping table
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
        doc_types = DocumentType.objects.filter(is_active=True).values('id', 'type_name',"allowed_extensions")
        
        # 2. Fetch Workflows from workflows_workflow table via the ExternalWorkflow model. 
        workflows = ExternalWorkflow.objects.all().values('id', 'name')
        
        return Response({
            "document_types": list(doc_types),
            "workflows": list(workflows)
        }, status=200)
        
    except Exception as e:
        return Response({"error": str(e)}, status=500)


class GenerateUploadLinkView(APIView):
    """Internal API: Creates a new secure upload link."""
    # Temporarily AllowAny for testing, change to IsAuthenticated later
    permission_classes = [AllowAny] 

    def post(self, request):
        doc_type_id = request.data.get('document_type_id')
        workflow_id = request.data.get('workflow_id')
        expiry_days = int(request.data.get('expiry_days', 7)) # Defaults to 7 days

        if not doc_type_id or not workflow_id:
            return Response({"error": "document_type_id and workflow_id are required."}, status=400)

        try:
            doc_type = DocumentType.objects.get(id=doc_type_id)
            expires_at = timezone.now() + datetime.timedelta(days=expiry_days)
            
            upload_link = DocumentUploadLink.objects.create(
                document_type=doc_type,
                workflow_id=str(workflow_id),
                expires_at=expires_at
            )
            
            # Construct the external-facing URL (Adjust port/domain as needed)
            link_url = f"http://localhost:5173/external-upload/{upload_link.id}"
            
            return Response({
                "message": "Upload link generated successfully.",
                "link_id": upload_link.id,
                "url": link_url,
                "expires_at": expires_at
            }, status=201)
            
        except DocumentType.DoesNotExist:
            return Response({"error": "Invalid Document Type."}, status=400)


class RevokeUploadLinkView(APIView):
    """Internal API: Kills an active upload link."""
    permission_classes = [AllowAny]

    def post(self, request, link_id):
        try:
            upload_link = DocumentUploadLink.objects.get(id=link_id)
            upload_link.is_revoked = True
            upload_link.save()
            return Response({"message": "Link has been successfully revoked."})
        except DocumentUploadLink.DoesNotExist:
            return Response({"error": "Link not found."}, status=404)


class LinkBasedUploadView(APIView):
    """External API: Handles the actual file upload using the UUID token."""
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny] # Must be AllowAny for external vendors

    def post(self, request, link_id):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "File is required."}, status=400)

        try:
            # 1. Validate the Token
            upload_link = DocumentUploadLink.objects.get(id=link_id)
            if not upload_link.is_valid():
                return Response({"error": "This upload link is expired or has been revoked."}, status=403)

            doc_type = upload_link.document_type
            
            # 2. Strict File Type Validation
            file_ext = file_obj.name.split('.')[-1].lower()
            allowed_exts = [ext.strip().lower() for ext in doc_type.allowed_extensions.split(',')]
            if file_ext not in allowed_exts:
                return Response({"error": f"Invalid format. Allowed: {doc_type.allowed_extensions}"}, status=400)

            # 3. SHA-256 Duplicate Check
            file_content = file_obj.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            if Document.objects.filter(file_hash=file_hash).exists():
                return Response({"error": "This document has already been uploaded."}, status=409)

            # 4. S3 Upload & AI Summarization
            mime_type = file_obj.content_type
            file_name = file_obj.name
            
            s3_service = S3Service()
            ai_service = DocumentAIService()
            
            s3_url = s3_service.upload_file_bytes(file_content, file_name, mime_type)
            summary_text = ai_service.generate_summary(file_content, mime_type)

            # 5. Save Core Document
            new_doc = Document.objects.create(
                document_name=file_name,
                document_type=doc_type,
                source='api_link',
                current_status='uploaded',
                file_hash=file_hash,
                ai_summary=summary_text,
                s3_url=s3_url
            )

            # 6. Trigger the Workflow Engine Handshake
            ExternalWorkflowInstance.objects.create(
                workflow_id=upload_link.workflow_id,
                document_name=new_doc.document_name,
                document_type=doc_type.type_name,
                status='RUNNING',
                current_state='Start',
                created_at=timezone.now(),
                updated_at=timezone.now(),
                started_at=timezone.now(),
                payload=json.dumps({
                    "document_id": str(new_doc.id),
                    "source": "External Link Upload",
                    "ai_summary": summary_text
                }),
                runtime_state="{}"
            )

            return Response({
                "message": "File securely uploaded and workflow triggered.",
                "document_id": new_doc.id
            }, status=201)

        except DocumentUploadLink.DoesNotExist:
            return Response({"error": "Invalid upload link."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class ListUploadLinksView(APIView):
    """Internal API: Lists all generated upload links for the admin dashboard."""
    permission_classes = [AllowAny]

    def get(self, request):
        links = DocumentUploadLink.objects.select_related('document_type').all().order_by('-created_at')
        data = []
        for item in links:
            data.append({
                "id": str(item.id),
                "document_type_name": item.document_type.type_name,
                "workflow_id": item.workflow_id,
                "is_revoked": item.is_revoked,
                "is_valid": item.is_valid(),
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M"),
                "expires_at": item.expires_at.strftime("%Y-%m-%d %H:%M"),
                "url": f"http://localhost:5173/external-upload/{item.id}"
            })
        return Response(data, status=200)

        