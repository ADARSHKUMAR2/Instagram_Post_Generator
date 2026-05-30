from fastapi import FastAPI, HTTPException
import uvicorn
import traceback
from agent.schemas import PostRequest, PostResponse, InstaPost
from agent.agent_handler import generate_instagram_post
import replicate
from shared.config import Config
import urllib.parse

app = FastAPI(
    title="InstaAgent Backend",
    description="Main API for the Instagram Auto-Poster",
    version="1.0.0"
)

@app.get("/")
async def root_landing():
    """
    Simple landing page to confirm the central brain is online.
    """
    return {
        "status": "online",
        "message": "InstaAgent Central Brain is running. Visit /docs for the interactive API explorer."
    }

@app.post("/api/generate-post", response_model=PostResponse)
async def api_generate_post(request: PostRequest):
    """
    Receives a category from the frontend and triggers the AI pipeline.
    """
    try:
        # Pass the validated request string to your agent handler
        final_content = await generate_instagram_post(request.prompt)
        insta_post = InstaPost(**final_content)
        
        # 2. Call DALL-E 3 with the generated prompt
        image_url = None
        # 2. Generate the Free Pollinations Image URL
        print("🎨 Generating free image URL via Pollinations.ai...")
        
        # We must URL-encode the prompt so it's safe to put in a web link
        clean_prompt = insta_post.image_prompt.replace('\n', ' ').replace('\r', '').strip()
        
        # Browsers hate massively long URLs, so we cap the prompt at 800 characters
        if len(clean_prompt) > 800:
            clean_prompt = clean_prompt[:800]
            
        safe_prompt = urllib.parse.quote(clean_prompt)
        # Construct the URL (Using the FLUX model for free photorealism)
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&model=flux&nologo=true"
        
        print(f"✅ Image URL created: {image_url}")

        # 3. Return the complete package to the frontend
        return PostResponse(
            status="success",
            content=insta_post,
            image_url=image_url 
        )
        
    except Exception as e:
        print("--- FULL TRACEBACK START ---")
        traceback.print_exc()
        print("--- FULL TRACEBACK END ---")
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    # Run this backend from the root directory using:
    # python backend/api.py  OR  uvicorn backend.api:app --reload
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)