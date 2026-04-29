from rest_framework import serializers
from .models import Document, DocumentType #import my specific database tables (models) from the current directory

class DocumentTypeSerializer(serializers.ModelSerializer): # Send data from the DocumentType table to the frontend.
    class Meta:
        model = DocumentType     #which of my database tables now use
        fields = ['id', 'type_name', 'category', 'allowed_extensions', 'is_active']  #which seleccted fields from the DocumentType table to send to the frontend. 

class DocumentSerializer(serializers.ModelSerializer): # Send data from the Document table to the frontend. 
    # This reads the string name of the document type to send to the frontend
    document_type_name = serializers.CharField(source='document_type.type_name', read_only=True) 
     #this reads the string name of the document type from the related DocumentType table and sends it to the frontend as 'document_type_name'. It's read-only because.
    
    class Meta:
        model = Document
        fields = ['id', 'document_name', 'document_type', 'document_type_name', 'source', 'current_status', 'submitted_date', 'file_hash', 'ai_summary', 's3_url', 'updated_at']        # This specifies which fields from the Document table to send to the frontend, including the related document type name.    