import os
from agents import OpenAIChatCompletionsModel
from dotenv import load_dotenv
from enum import Enum
from openai import AsyncOpenAI

load_dotenv()

# IS_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"

# Dynamically set the routing names based on the environment
BASE_WEATHER_URL = "weather-mcp" 
BASE_NEWS_URL = "news-mcp" 
BASE_SPORTS_URL = "sports-mcp" 

class MCPServerName(str, Enum):
    WEATHER = "weather"
    NEWS = "news"
    # SPORTS = "sports"
    FACTS="facts"
    PUBLISH = "publish"

class Config:
    MCP_SERVERS = {
        MCPServerName.WEATHER: {
            "url": f"http://{BASE_WEATHER_URL}:8001/sse",
        },
        MCPServerName.NEWS: {
            "url": f"http://{BASE_NEWS_URL}:8002/sse",
        },
        # MCPServerName.SPORTS: {
        #     "url": f"http://{BASE_SPORTS_URL}:8003/sse",
        #     "headers": {"Host": "localhost"}  # Bypass FastMCP SSRF block
        # }
    }

    github_token = os.getenv("GITHUB_TOKEN")
    openai_key=os.getenv("OPENAI_API_KEY")

    MODEL = "gpt-4o-mini"

    IG_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID")
    ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")

    github_client = AsyncOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=github_token)

    github_model = OpenAIChatCompletionsModel(
        model=MODEL,
        openai_client=github_client
    )
     
    image_model = "black-forest-labs/flux-2-pro"