from fastapi import FastAPI, HTTPException
import uvicorn
import traceback
from agent.schemas import PostRequest, PostResponse, InstaPost
from agent.agent_handler import generate_instagram_post

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
        
        return PostResponse(
            status="success",
            content=InstaPost(**final_content)
        )
        
    except Exception as e:
        # If an MCP server is down or OpenAI fails, return a 500 error cleanly
        print("--- FULL TRACEBACK START ---")
        traceback.print_exc()
        print("--- FULL TRACEBACK END ---")
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    # Run this backend from the root directory using:
    # python backend/api.py  OR  uvicorn backend.api:app --reload
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)