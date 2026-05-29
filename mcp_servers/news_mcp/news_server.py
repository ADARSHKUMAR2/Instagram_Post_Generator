import uvicorn
from fastapi import FastAPI
from news_mcp import mcp

app = FastAPI(title="News MCP Server")

@app.get("/status")
async def get_status():
    return {"status": "online", "service": "Live RSS News Provider"}

base_sse_app = mcp.sse_app()

async def spoofed_sse_app(scope, receive, send):
    if scope["type"] == "http":
        new_headers = []
        for k, v in scope.get("headers", []):
            key = k.lower()
            if not key.startswith(b"x-forwarded-") and key not in (b"host", b"origin", b"referer"):
                new_headers.append((k, v))
        
        new_headers.append((b"host", b"127.0.0.1:8002"))
        new_headers.append((b"origin", b"http://127.0.0.1:8002"))
        
        scope["headers"] = new_headers
        scope["client"] = ("127.0.0.1", 50000)
        scope["server"] = ("127.0.0.1", 8002)

    await base_sse_app(scope, receive, send)

app.mount("/", spoofed_sse_app)

if __name__ == "__main__":
    uvicorn.run("news_server:app", host="0.0.0.0", port=8002, reload=True)