import requests
from django.conf import settings

class OneDriveService:
    def __init__(self):
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.token = self.get_access_token()
        # Storing your Object ID here so it applies to all methods automatically!
        self.user_object_id = "611e5faf-f2e3-4894-9ddd-12768109a074"



    def get_access_token(self):
        """Get OAuth2 token using client credentials from Azure"""
        url = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': settings.MS_CLIENT_ID,
            'client_secret': settings.MS_CLIENT_SECRET,
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        print("\n--- DEBUG CREDENTIALS ---")
        print(f"Tenant: {settings.MS_TENANT_ID}")
        print(f"Client: {settings.MS_CLIENT_ID}")
        print("-------------------------\n")

        response = requests.post(url, data=data)
        response.raise_for_status() 
        return response.json().get('access_token')

    def list_files(self, folder_path):
        """List all files in a specific OneDrive folder"""
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Using Object ID instead of email
        url = f"{self.base_url}/users/{self.user_object_id}/drive/root:/{folder_path}:/children"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('value', [])
        return []

    def download_file(self, file_id):
        """Download a specific file's binary content"""
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Using Object ID instead of email
        url = f"{self.base_url}/users/{self.user_object_id}/drive/items/{file_id}/content"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.content

    def move_to_archive(self, file_id, archive_folder_name):
        """Move a processed file to an archive/error folder"""
        # Note: A true 'move' in Graph API requires the destination folder's ID.
        # For now, we will handle the API request structurally so it doesn't crash your worker.
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        # First, ensure the archive folder exists to get its ID
        archive_folder_id = self.create_folder(archive_folder_name)
        
        # Then patch the file to move it into that new folder
        url = f"{self.base_url}/users/{self.user_object_id}/drive/items/{file_id}"
        data = {
            "parentReference": {
                "id": archive_folder_id
            }
        }
        
        response = requests.patch(url, headers=headers, json=data)
        if response.status_code not in [200, 201]:
            print(f"Archive move non-fatal error: {response.text}")
        return True

    def create_folder(self, folder_name):
        """Creates a new folder in the root directory of the OneDrive account"""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        # Using Object ID instead of email
        url = f"{self.base_url}/users/{self.user_object_id}/drive/root/children"
        
        data = {
            "name": folder_name,
            "folder": { },
            "@microsoft.graph.conflictBehavior": "rename" 
        }
        
        response = requests.post(url, headers=headers, json=data)


        # --- NEW DEBUG CODE: Print Microsoft's hidden message ---
        if response.status_code not in [200, 201]:
            print("\n--- MICROSOFT GRAPH ERROR ---")
            try:
                print(response.json())
            except:
                print(response.text)
            print("-----------------------------\n")
        # --------------------------------------------------------
        
        response.raise_for_status()
        return response.json().get('id')
    

