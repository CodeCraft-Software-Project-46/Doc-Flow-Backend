import hashlib
import json
from celery import shared_task
from documents.gdrive_service import GDriveService
from documents.ai_service import DocumentAIService
from documents.models import GDriveFolderMapping, Document, GoogleDriveDocument, ExternalWorkflowInstance
from django.utils import timezone
from documents.s3_service import S3Service

@shared_task
def scan_all_mapped_folders():
    print("\n--- Starting Google Drive Scan ---")
    drive_service = GDriveService()
    ai_service = DocumentAIService()
    s3_service = S3Service()
    
    # 1. PASTE YOUR ARCHIVE FOLDER ID HERE
    ARCHIVE_FOLDER_ID = "1WwRXG99rGtH_RIx-dueLtZV3luQIzmKd"
    
    # 2. Get active folders
    mapped_folders = GDriveFolderMapping.objects.filter(is_active=True)
    
    if not mapped_folders:
        print("No active folder mappings found in the database.")
        return "No folders to scan."
        
    for mapping in mapped_folders:
        folder_id = mapping.gdrive_folder_id
        print(f"Scanning folder: {mapping.folder_name} ({folder_id})")
        
        files = drive_service.list_files(folder_id)
        
        if not files:
            print(f"No new files found in {mapping.folder_name}.")
            continue
            
        for file in files:
            file_id = file['id']
            file_name = file['name']
            print(f"Found incoming file: {file_name}")
            
            try:
                # 3. Download and Hash
                file_content = drive_service.download_file(file_id)
                file_hash = hashlib.sha256(file_content).hexdigest()
                
                # Check for duplicates
                if Document.objects.filter(file_hash=file_hash).exists():
                    print(f"Duplicate detected! Moving {file_name} to archive without saving.")
                    drive_service.move_to_archive(file_id, ARCHIVE_FOLDER_ID)
                    continue
                
                # 4. AI Pre-Processing
                mime_type = file.get('mimeType', 'application/pdf') 
                summary_text = ai_service.generate_summary(file_content, mime_type)
                print(f"AI Summary generated: {summary_text[:50]}...")
                
                # ... (AI Summary generation is above here) ...

                # 4.5 NEW: Upload directly to AWS S3
                print("Uploading file to AWS S3 Secure Storage...")
                s3_url = s3_service.upload_file_bytes(file_content, file_name, mime_type)

                # 5. Save to AWS Database
                new_doc = Document.objects.create(
                    document_name=file_name,
                    source='gdrive',
                    current_status='uploaded',
                    file_hash=file_hash,
                    ai_summary=summary_text,
                    s3_url=s3_url # <-- Save the S3 URL!
                )
                
                # 6. Save Google tracking data
                GoogleDriveDocument.objects.create(
                    document=new_doc,
                    gdrive_file_id=file_id,
                    file_name=file_name
                )
                
                # 7. THE HANDSHAKE (Triggering Awishka's Engine)
                # ... (Keep your exact WorkflowInstance.objects.create code here) ...
                
                # 8. Destroy the Google Drive Original (Clean up)
                # Instead of moving it to an archive folder, we just trash the original 
                # because the master copy is now safely locked in AWS S3.
                drive_service.move_to_archive(file_id, ARCHIVE_FOLDER_ID)
                
                print(f"✅ Securely stored in S3, summarized, and workflow triggered: {file_name}")
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
                continue