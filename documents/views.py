import hashlib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentType, ManualUploadDocument

class ManualUploadView(APIView): # This view handles manual document uploads, ensuring no duplicates and proper metadata storage
    parser_classes = (MultiPartParser, FormParser) # Allow handling of file uploads and form data

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