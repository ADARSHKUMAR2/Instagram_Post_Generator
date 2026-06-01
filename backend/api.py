import os
import uvicorn
import traceback
import requests
import urllib.parse
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from shared.config import Config
from agent.schemas import PostRequest, PostResponse, InstaPost, PublishRequest, SearchQuery
from agent.agent_handler import generate_instagram_post
from datetime import datetime
import sqlite3
from infrastructure.services.db_manager import DatabaseManager
from infrastructure.services.scheduler import start_scheduler
from infrastructure.services.aws_s3 import StorageHandoffManager
from infrastructure.services.google_drive import GoogleDriveManager
from infrastructure.services.discord_notifier import DiscordManager
from infrastructure.services.vector_manager import VectorManager

app = FastAPI(
    title="InstaAgent Backend",
    description="Main API for the Instagram Auto-Poster",
    version="1.0.0"
)
router = APIRouter()

# Initialize managers once at runtime
storage_manager = StorageHandoffManager()
drive_manager = GoogleDriveManager()
discord_manager = DiscordManager()
db_manager = DatabaseManager()
vector_manager = VectorManager()

class DrivePublishRequest(BaseModel):
    drive_file_id: str
    caption: str

class QueueRequest(BaseModel):
    source_type: str # 'drive' or 'pollinations'
    file_id_or_url: str
    caption: str
    scheduled_time: datetime 

@app.get("/")
async def root_landing():
    return {
        "status": "online",
        "message": "InstaAgent Central Brain is running. Visit /docs for the interactive API explorer."
    }

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@router.post("/api/queue-post")
async def queue_post(payload: QueueRequest):
    try:
        post_id = db_manager.add_to_queue(
            payload.source_type, 
            payload.file_id_or_url, 
            payload.caption, 
            payload.scheduled_time
        )
        return {"status": "success", "message": f"Post #{post_id} added to the queue!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/queue-status")
async def get_queue_status():
    """Fetches the entire post queue for the Streamlit dashboard."""
    try:
        # We need a quick ad-hoc query to get everything, not just 'pending'
        with sqlite3.connect(db_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM post_queue ORDER BY scheduled_time ASC")
            posts = [dict(row) for row in cursor.fetchall()]
            return {"status": "success", "queue": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/queue/{post_id}")
async def delete_queued_post(post_id: int):
    """Allows the user to cancel a scheduled post."""
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM post_queue WHERE id = ?", (post_id,))
            conn.commit()
            return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/generate-post", response_model=PostResponse)
async def api_generate_post(request: PostRequest):
    try:
        final_content = await generate_instagram_post(request.prompt)
        insta_post = InstaPost(**final_content)
        
        print("🎨 Generating free image URL via Pollinations.ai...")
        clean_prompt = insta_post.image_prompt.replace('\n', ' ').replace('\r', '').strip()
        
        if len(clean_prompt) > 800:
            clean_prompt = clean_prompt[:800]
            
        safe_prompt = urllib.parse.quote(clean_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&model=flux&nologo=true"
        
        print(f"✅ Image URL created: {image_url}")

        return PostResponse(
            status="success",
            content=insta_post,
            image_url=image_url 
        )
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/api/publish-post")
async def api_publish_post(request: PublishRequest):
    if not Config.IG_ACCOUNT_ID or not Config.ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Missing Instagram API credentials.")

    try:
        print("📲 Step 1: Creating Instagram Media Container...")
        container_url = f"https://graph.facebook.com/v19.0/{Config.IG_ACCOUNT_ID}/media"
        container_payload = {
            "image_url": request.image_url,
            "caption": request.caption,
            "access_token": Config.ACCESS_TOKEN
        }
        
        container_res = requests.post(container_url, data=container_payload)
        container_data = container_res.json()
        
        if "id" not in container_data:
            raise Exception(f"Container creation failed: {container_data}")
            
        creation_id = container_data["id"]
        print(f"✅ Container created! ID: {creation_id}")
        
        print("🚀 Step 2: Publishing to Instagram feed...")
        publish_url = f"https://graph.facebook.com/v19.0/{Config.IG_ACCOUNT_ID}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": Config.ACCESS_TOKEN
        }
        
        publish_res = requests.post(publish_url, data=publish_payload)
        publish_data = publish_res.json()
        
        if "id" not in publish_data:
            raise Exception(f"Publishing failed: {publish_data}")
            
        print("🔔 Pinging Discord...")
        discord_manager.send_success_notification(request.caption, request.image_url)

        return {"status": "success", "message": "Post published successfully!", "ig_post_id": publish_data["id"]}

    except Exception as e:
        print(f"🚨 Publish Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/publish-from-drive")
async def publish_from_drive(payload: DrivePublishRequest):
    if not Config.IG_ACCOUNT_ID or not Config.ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Missing Instagram API credentials.")

    local_image_name = f"drive_{payload.drive_file_id}.jpg"
    local_path = f"/tmp/{local_image_name}"
    
    try:
        # Phase 1: Pull down from Google Drive
        drive_manager.download_file_from_drive(payload.drive_file_id, local_path)
        
        # Phase 2: Stage to public AWS S3 bucket
        public_url = storage_manager.upload_temporary_image(local_path, local_image_name)
        
        # Phase 3: Fire Meta API Container Creation with the public S3 url
        print("📲 Step 1 (Drive-Pipe): Creating Instagram Media Container...")
        container_url = f"https://graph.facebook.com/v19.0/{Config.IG_ACCOUNT_ID}/media"
        container_payload = {
            "image_url": public_url,
            "caption": payload.caption,
            "access_token": Config.ACCESS_TOKEN
        }
        
        container_res = requests.post(container_url, data=container_payload)
        container_data = container_res.json()
        
        if "id" not in container_data:
            raise Exception(f"Container creation failed: {container_data}")
            
        creation_id = container_data["id"]
        print(f"✅ Container created from S3! ID: {creation_id}")
        
        print("🚀 Step 2 (Drive-Pipe): Publishing to Instagram feed...")
        publish_url = f"https://graph.facebook.com/v19.0/{Config.IG_ACCOUNT_ID}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": Config.ACCESS_TOKEN
        }
        
        publish_res = requests.post(publish_url, data=publish_payload)
        publish_data = publish_res.json()
        
        if "id" not in publish_data:
            raise Exception(f"Publishing failed: {publish_data}")
        
        print("🔔 Pinging Discord...")
        # --- Clean, 1-line notification trigger ---
        discord_manager.send_success_notification(payload.caption, public_url)

        return {
            "status": "success", 
            "message": "Post pulled from Drive, processed via S3, and pushed to Instagram!",
            "ig_post_id": publish_data["id"]
        }
        
    except Exception as e:
        print(f"🚨 Pipeline Execution Error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution broke: {str(e)}")
        
    finally:
        # Phase 4: Enforce strict storage hygiene
        storage_manager.purge_temporary_image(local_image_name)
        if os.path.exists(local_path):
            os.remove(local_path)

@router.post("/api/search-drive")
async def search_drive_images(search_data: SearchQuery):
    """
    Takes a plain-text prompt, converts it to an embedding,
    and returns matching Google Drive file IDs.
    """
    if not search_data.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
    print(f"🔍 Executing semantic image search for: '{search_data.query}'")
    matching_ids = vector_manager.search(search_data.query, top_k=search_data.top_k)
    
    return {
        "query": search_data.query,
        "results": matching_ids  # List of Google Drive file IDs
    }
    
# Register all routes directly onto the main application instance
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)