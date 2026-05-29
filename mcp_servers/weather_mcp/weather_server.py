import uvicorn
from fastapi import FastAPI
from weather_mcp import mcp

# Create the FastAPI app
app = FastAPI(title="Weather MCP Server")

# Regular FastAPI route for health checks
@app.get("/status")
async def get_status():
    """Check if the Weather API is running."""
    return {"status": "online", "service": "Weather Data Provider"}

# Mount the MCP SSE app to expose the tools to AI Agents
app.mount("/", mcp.sse_app())

if __name__ == "__main__":
    # Run this specific MCP server on port 8001
    uvicorn.run("weather_server:app", host="0.0.0.0", port=8001, reload=True)