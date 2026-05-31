import io
import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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