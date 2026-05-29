import os
from agents import OpenAIChatCompletionsModel
from dotenv import load_dotenv
from enum import Enum
from openai import AsyncOpenAI

load_dotenv()

class MCPServerName(str, Enum):
    WEATHER = "weather"
    NEWS = "news"
    SPORTS = "sports"
    FACTS="facts"
    PUBLISH = "publish"

class Config:
    MCP_SERVERS = {
        MCPServerName.WEATHER: {"url": "http://localhost:8001/sse"},
        MCPServerName.NEWS: {"url": "http://localhost:8002/sse"},
        MCPServerName.SPORTS: {"url": "http://localhost:8003/sse"}
    }

    github_token = os.getenv("GITHUB_TOKEN")
    openai_key=os.getenv("OPENAI_API_KEY")

    MODEL = "gpt-4o-mini"

    github_client = AsyncOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=github_token)

    github_model = OpenAIChatCompletionsModel(
        model=MODEL,
        openai_client=github_client
    )
