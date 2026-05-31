import os
import uvicorn
import traceback
import requests
import urllib.parse
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from shared.config import Config
from agent.schemas import PostRequest, PostResponse, InstaPost, PublishRequest
from agent.agent_handler import generate_instagram_post
from infrastructure.services.aws_s3 import StorageHandoffManager
from infrastructure.services.google_drive import GoogleDriveManager

app = FastAPI(
    title="InstaAgent Backend",
    description="Main API for the Instagram Auto-Poster",
    version="1.0.0"
)
router = APIRouter()

# Initialize managers once at runtime
storage_manager = StorageHandoffManager()
drive_manager = GoogleDriveManager()

class DrivePublishRequest(BaseModel):
    drive_file_id: str
    caption: str

@app.get("/")
async def root_landing():
    return {
        "status": "online",
        "message": "InstaAgent Central Brain is running. Visit /docs for the interactive API explorer."
    }

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
        notify_discord(request.caption, request.image_url)

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
        notify_discord(payload.caption, payload.image_url)

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

def notify_discord(caption: str, image_url: str):
    """Fires a rich embed notification to Discord if a webhook is configured."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("⚠️ No Discord webhook configured. Skipping notification.")
        return
        
    payload = {
        "content": "🚀 **New Post Successfully Published to Instagram!**",
        "embeds": [
            {
                "description": f"**Caption:**\n{caption}",
                "color": 13773097, # Instagram Pink/Purple hex color
                "image": {"url": image_url}
            }
        ]
    }
    
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Discord Webhook silently failed: {e}")

# Register all routes directly onto the main application instance
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)