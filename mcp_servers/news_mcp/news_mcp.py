from mcp.server.fastmcp import FastMCP
from news_service import NewsService

# Initialize the MCP Server
mcp = FastMCP("News Server")

# Create a service instance
news_service = NewsService()

@mcp.tool()
def fetch_news(category: str) -> str:
    """
    Get the top 5 breaking news headlines for a specific category or topic.
    Use this tool whenever you need current events, sports scores, tech updates, 
    or global news to draft a relevant post.
    """
    return news_service.get_top_news(category)