import os
import logging
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StorageHandoffManager:
    def __init__(self):
        self.bucket_name = os.getenv("STORAGE_BUCKET_NAME", "your-instagram-handoff-bucket")
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("STORAGE_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("STORAGE_SECRET_KEY")
        )

    def upload_temporary_image(self, file_path: str, object_name: str) -> str:
        """
        Uploads an image file to S3 and forces a public-read jpeg header.
        """
        try:
            extra_args = {
                'ContentType': 'image/jpeg'
            }
            logger.info(f"📤 Uploading {file_path} to S3...")
            self.s3_client.upload_file(file_path, self.bucket_name, object_name, ExtraArgs=extra_args)
            
            public_url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_name}"
            logger.info(f"🔗 Direct Public URL generated: {public_url}")
            return public_url

        except ClientError as e:
            logger.error(f"❌ S3 upload failed: {e}")
            raise e

    def purge_temporary_image(self, object_name: str):
        """
        Deletes the image file from S3 to maintain zero footprint.
        """
        try:
            logger.info(f"🗑️ Purging temporary object '{object_name}' from S3...")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info("✅ S3 temporary storage cleared.")
        except ClientError as e:
            logger.error(f"⚠️ Failed to remove file from S3: {e}")