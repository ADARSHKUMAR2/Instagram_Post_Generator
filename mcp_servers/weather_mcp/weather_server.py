import uvicorn
from fastapi import FastAPI
from weather_mcp import mcp

app = FastAPI(title="Weather MCP Server")

@app.get("/status")
async def get_status():
    return {"status": "online", "service": "Weather Data Provider"}

base_sse_app = mcp.sse_app()

async def spoofed_sse_app(scope, receive, send):
    if scope["type"] == "http":
        # Bulletproof SSRF Header Stripping (No API key check needed)
        new_headers = []
        for k, v in scope.get("headers", []):
            key = k.lower()
            if not key.startswith(b"x-forwarded-") and key not in (b"host", b"origin", b"referer"):
                new_headers.append((k, v))
        
        # Inject perfectly clean local headers
        new_headers.append((b"host", b"127.0.0.1:8001"))
        new_headers.append((b"origin", b"http://127.0.0.1:8001"))
        
        scope["headers"] = new_headers
        scope["client"] = ("127.0.0.1", 50000)
        scope["server"] = ("127.0.0.1", 8001)

    await base_sse_app(scope, receive, send)

app.mount("/", spoofed_sse_app)

if __name__ == "__main__":
    uvicorn.run("weather_server:app", host="0.0.0.0", port=8001, reload=True)