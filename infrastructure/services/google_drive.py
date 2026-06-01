import io
import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_DRIVE_FOLDER_ID = "1MTGCSnQbhPee6sls8K7yxMqzI83ZpkFu"

class GoogleDriveManager:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/google_creds.json")
        
        if not os.path.exists(self.creds_path):
            raise FileNotFoundError(f"Missing Google credentials file at {self.creds_path}")
            
        self.creds = service_account.Credentials.from_service_account_file(
            self.creds_path, scopes=self.scopes
        )
        self.service = build('drive', 'v3', credentials=self.creds)

    def download_file_from_drive(self, file_id: str, destination_path: str):
        try:
            logger.info(f"📥 Downloading file ID {file_id} from Google Drive...")
            request = self.service.files().get_media(fileId=file_id)
            
            fh = io.FileIO(destination_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            logger.info(f"✅ File saved locally to {destination_path}")
            return destination_path
        except Exception as e:
            logger.error(f"❌ Google Drive down-stream broke: {e}")
            raise e

    def upload_image(self, local_file_path: str, drive_folder_id: str) -> str:
        """Uploads a local image to a specific Google Drive folder."""
        file_metadata = {
            'name': os.path.basename(local_file_path),
            'parents': [drive_folder_id]
        }
        media = MediaFileUpload(local_file_path, mimetype='image/jpeg', resumable=True)
        
        uploaded_file = self.service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        
        return uploaded_file.get('id')

    def list_images(self, folder_id: str = TARGET_DRIVE_FOLDER_ID):
        """Scans a specific Google Drive folder for image files."""
        try:
            logger.info(f"🔍 Scanning Drive folder {folder_id} for images...")
            # Query explicitly for images inside the target folder
            query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
            
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType)"
            ).execute()
            
            items = results.get('files', [])
            return items
            
        except Exception as e:
            logger.error(f"❌ Failed to list images: {e}")
            return []