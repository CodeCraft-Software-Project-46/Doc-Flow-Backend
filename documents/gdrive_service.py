import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from django.conf import settings

class GDriveService:
    def __init__(self):
        # Point this to the JSON file you downloaded
        self.creds_path = os.path.join(settings.BASE_DIR, os.environ.get('GOOGLE_CREDENTIALS_PATH', 'google_credentials.json'))
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.creds = service_account.Credentials.from_service_account_file(
            self.creds_path, scopes=self.scopes
        )
        self.service = build('drive', 'v3', credentials=self.creds)

    def create_folder(self, folder_name, parent_folder_id=None):
        """Creates a new folder in Google Drive"""
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]

        folder = self.service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

    def list_files(self, folder_id):
        """List all files inside a specific Google Drive folder ID"""
        query = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
        results = self.service.files().list(
            q=query, spaces='drive', fields='files(id, name, mimeType)'
        ).execute()
        return results.get('files', [])

    def download_file(self, file_id):
        """Download a specific file's binary content"""
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()

    def move_to_archive(self, file_id, archive_folder_id):
        """Move a processed file to an archive folder"""
        # Retrieve the existing parents to remove
        file = self.service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))

        # Move the file to the new folder
        file = self.service.files().update(
            fileId=file_id,
            addParents=archive_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        return file.get('id')
    
    def trash_file(self, file_id):
        """
        Moves the processed file to the Google Drive Trash.
        It will automatically be permanently deleted by Google after 30 days.
        """
        try:
            print(f"Moving file {file_id} to Google Drive Trash...")
            self.service.files().update(
                fileId=file_id, 
                body={'trashed': True}
            ).execute()
            print("Successfully trashed original file.")
        except Exception as e:
            print(f"❌ Failed to trash file {file_id}: {str(e)}")
            # We don't raise the error here because the file is already safe in AWS S3. 
            # We just log it so the worker doesn't crash over a cleanup task.