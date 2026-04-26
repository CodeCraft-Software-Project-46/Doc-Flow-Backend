import hashlib
from celery import shared_task
from documents.gdrive_service import GDriveService
from documents.models import GDriveFolderMapping, Document, GoogleDriveDocument

@shared_task
def scan_all_mapped_folders():
    print("\n--- Starting Google Drive Scan ---")
    drive_service = GDriveService()
    
    # 1. PASTE YOUR ARCHIVE FOLDER ID HERE (From your Google Drive URL)
    ARCHIVE_FOLDER_ID = "1WwRXG99rGtH_RIx-dueLtZV3luQIzmKd"
    
    # 2. Get all active folders we mapped in the database
    mapped_folders = GDriveFolderMapping.objects.filter(is_active=True)
    
    if not mapped_folders:
        print("No active folder mappings found in the database.")
        return "No folders to scan."
        
    for mapping in mapped_folders:
        folder_id = mapping.gdrive_folder_id
        print(f"Scanning folder: {mapping.folder_name} ({folder_id})")
        
        # 3. List the files sitting in Google Drive
        files = drive_service.list_files(folder_id)
        
        if not files:
            print(f"No new files found in {mapping.folder_name}.")
            continue
            
        for file in files:
            file_id = file['id']
            file_name = file['name']
            print(f"Found incoming file: {file_name}")
            
            try:
                # 4. Download file content to generate a unique digital fingerprint (hash)
                file_content = drive_service.download_file(file_id)
                file_hash = hashlib.sha256(file_content).hexdigest()
                
                # Check if we already processed this exact file before (Anti-Duplicate)
                if Document.objects.filter(file_hash=file_hash).exists():
                    print(f"Duplicate detected! Moving {file_name} to archive without saving.")
                    drive_service.move_to_archive(file_id, ARCHIVE_FOLDER_ID)
                    continue
                
                # 5. Save the main record to your Document table
                new_doc = Document.objects.create(
                    document_name=file_name,
                    source='gdrive',
                    current_status='uploaded',
                    file_hash=file_hash,
                )
                
                # 6. Save the Google-specific tracking data
                GoogleDriveDocument.objects.create(
                    document=new_doc,
                    gdrive_file_id=file_id,
                    file_name=file_name
                )
                
                # 7. Move the physical file to the Archive folder
                drive_service.move_to_archive(file_id, ARCHIVE_FOLDER_ID)
                print(f"✅ Successfully saved to AWS DB and archived: {file_name}")
                
            except Exception as e:
                print(f"❌ Error processing {file_name}: {str(e)}")
                
    print("--- Scan Complete ---\n")
    return "Scan complete!"