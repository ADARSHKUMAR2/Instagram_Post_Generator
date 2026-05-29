from mcp.server.fastmcp import FastMCP
from news_service import NewsService

# Initialize the MCP Server
mcp = FastMCP("News Server")

# Create a service instance
news_service = NewsService()

@mcp.tool()
async def fetch_news(category: str) -> str:
    """
    Get the top 5 breaking news headlines.
    
    CRITICAL ROUTING INSTRUCTIONS FOR THE AI:
    - IF the user asks for a SPECIFIC topic (e.g., "UEFA Champions League", "Ranveer Singh", "Apple"), you MUST pass that EXACT phrase as the query. Do not summarize it.
    - IF the user asks for a GENERAL category (e.g., "Sports", "Technology", "World News"), pass that general category word as the query."""
    print(f"\n🔍 [NEWS MCP] The AI Agent requested news for: '{category}'")

    data = await news_service.get_top_news(category)

    print(f"📤 [NEWS MCP] Returning this exact payload to the Agent:")
    print("-" * 50)
    print(data)
    print("-" * 50 + "\n")

    return data
