from rest_framework import serializers
from .models import Document, DocumentType, ManualUploadDocument #import my specific database tables (models) from the current directory

import boto3
from django.conf import settings

class DocumentTypeSerializer(serializers.ModelSerializer): # Send data from the DocumentType table to the frontend.
    class Meta:
        model = DocumentType     #which of my database tables now use
        fields = ['id', 'type_name', 'category', 'is_active', 'allowed_extensions']  #which seleccted fields from the DocumentType table to send to the frontend. 

# ... (DocumentTypeSerializer stays the same) ...

class DocumentSerializer(serializers.ModelSerializer):
    document_type_name = serializers.CharField(source='document_type.type_name', read_only=True) 
    
    # NEW: A custom field to generate the temporary VIP pass
    presigned_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 
            'document_name', 
            'source', 
            'document_type', 
            'document_type_name', 
            'current_status', 
            'file_hash', 
            'ai_summary', 
            's3_url', 
            'presigned_url', # <-- ADD THIS HERE!
            'submitted_date',
            'updated_at'
        ]

    def get_presigned_url(self, obj):
        # If there is no file, return nothing
        if not obj.s3_url:
            return None

        # Extract the exact "Key" (file path) from the full S3 URL
        # e.g., turns "https://mybucket.s3.amazonaws.com/uploads/file.pdf" into "uploads/file.pdf"
        object_key = obj.s3_url.split('.amazonaws.com/')[-1]

        # Connect to AWS
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        try:
            # Generate a link that is valid for 3600 seconds (1 hour)
            response = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': object_key
                },
                ExpiresIn=3600
            )
            return response
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            return None