from mcp.server.fastmcp import FastMCP
from weather_service import WeatherService

# Initialize the MCP Server
mcp = FastMCP("Weather Server")

# Create a service instance
weather_list = WeatherService()

@mcp.tool()
async def fetch_weather(city: str) -> str:
    """
    Get the current weather and temperature for a given city.
    Use this tool whenever you need to report on local weather conditions.
    """
    print(f"\n🌤️ [WEATHER MCP] The AI Agent requested weather for: '{city}'")
    
    data = await weather_list.get_current_weather(city)
    
    print(f"📤 [WEATHER MCP] Returning this exact payload to the Agent:")
    print("-" * 50)
    print(data)
    print("-" * 50 + "\n")
    
    return data