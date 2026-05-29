import uvicorn
from fastapi import FastAPI
from news_mcp import mcp

# Create the FastAPI app
app = FastAPI(title="News MCP Server")

# Regular FastAPI route for health checks
@app.get("/status")
async def get_status():
    """Check if the News API is running."""
    return {"status": "online", "service": "Live RSS News Provider"}

# Mount the MCP SSE app to expose the tools to AI Agents
# In your Agent config, this matches http://localhost:8002/sse
app.mount("/", mcp.sse_app())

if __name__ == "__main__":
    # Run this specific MCP server on port 8002
    uvicorn.run("news_server:app", host="0.0.0.0", port=8002, reload=True)