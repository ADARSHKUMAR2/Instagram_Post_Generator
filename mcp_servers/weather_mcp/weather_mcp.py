from mcp.server.fastmcp import FastMCP
from weather_service import WeatherService

# Initialize the MCP Server
mcp = FastMCP("Weather Server")

# Create a service instance
weather_list = WeatherService()

@mcp.tool()
def fetch_weather(city: str) -> str:
    """
    Get the current weather and temperature for a given city.
    Use this tool whenever you need to report on local weather conditions.
    """
    return weather_list.get_current_weather(city)