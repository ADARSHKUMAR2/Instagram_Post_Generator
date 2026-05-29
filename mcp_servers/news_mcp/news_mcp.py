from mcp.server.fastmcp import FastMCP
from news_service import NewsService

# Initialize the MCP Server
mcp = FastMCP("News Server")

# Create a service instance
news_service = NewsService()

@mcp.tool()
async def fetch_news(category: str) -> str:
    """
    Get the top 5 breaking news headlines for a specific category or topic.
    Use this tool whenever you need current events, sports scores, tech updates, 
    or global news to draft a relevant post.
    """
    print(f"\n🔍 [NEWS MCP] The AI Agent requested news for: '{category}'")

    data = await news_service.get_top_news(category)

    print(f"📤 [NEWS MCP] Returning this exact payload to the Agent:")
    print("-" * 50)
    print(data)
    print("-" * 50 + "\n")

    return data
