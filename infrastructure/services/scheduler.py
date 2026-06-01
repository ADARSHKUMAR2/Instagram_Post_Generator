import logging
from apscheduler.schedulers.background import BackgroundScheduler
from infrastructure.services.db_manager import DatabaseManager
from infrastructure.services.aws_s3 import StorageHandoffManager
from infrastructure.services.google_drive import GoogleDriveManager
from infrastructure.services.discord_notifier import DiscordManager
from shared.config import Config
import requests
import os

logger = logging.getLogger(__name__)

db = DatabaseManager()
storage_manager = StorageHandoffManager()
drive_manager = GoogleDriveManager()
discord_manager = DiscordManager()

def process_queue():
    """The main loop that checks the DB and publishes posts."""
    pending_posts = db.get_pending_posts()
    if not pending_posts:
        return

    logger.info(f"⏳ Found {len(pending_posts)} post(s) ready to publish.")

    for post in pending_posts:
        db.update_status(post['id'], 'processing')
        
        try:
            public_url = ""
            local_path = ""
            object_name = f"queued_{post['id']}.jpg"

            # 1. Asset Handoff Phase
            if post['source_type'] == 'drive':
                local_path = f"/tmp/{object_name}"
                drive_manager.download_file_from_drive(post['file_id_or_url'], local_path)
                public_url = storage_manager.upload_temporary_image(local_path, object_name)
            else:
                # If it's from Pollinations, it's already a public URL!
                public_url = post['file_id_or_url']

            # 2. Meta Publishing Phase
            logger.info("📲 Creating Meta Media Container...")
            container_url = f"https://graph.facebook.com/v19.0/{Config.IG_ACCOUNT_ID}/media"
            res = requests.post(container_url, data={
                "image_url": public_url,
                "caption": post['caption'],
                "access_token": Config.ACCESS_TOKEN
            }).json()
            
            if "id" not in res:
                raise Exception(f"Container failed: {res}")

            logger.info("🚀 Publishing to Feed...")
            pub_res = requests.post(f"https://graph.facebook.com/v19.0/{Config.IG_ACCOUNT_ID}/media_publish", data={
                "creation_id": res["id"],
                "access_token": Config.ACCESS_TOKEN
            }).json()

            if "id" not in pub_res:
                raise Exception(f"Publish failed: {pub_res}")

            # 3. Success & Cleanup Phase
            db.update_status(post['id'], 'completed')
            discord_manager.send_success_notification(post['caption'], public_url)

        except Exception as e:
            logger.error(f"❌ Failed to process post {post['id']}: {e}")
            db.update_status(post['id'], 'failed')

        finally:
            # Clean up S3 and local memory if it was a Drive post
            if post['source_type'] == 'drive':
                storage_manager.purge_temporary_image(object_name)
                if os.path.exists(local_path):
                    os.remove(local_path)

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run the check every 1 minute
    scheduler.add_job(process_queue, 'interval', minutes=1)
    scheduler.start()
    logger.info("⏱️ Background queue scheduler started.")