import asyncio
from pathlib import Path
from agents import Agent, Runner
from agents.mcp import MCPServerSse
from shared.config import Config, MCPServerName
from agent.prompts.insta_persona import Prompts

async def generate_instagram_post(category_request: str):
    
    # Connect to the MCP servers over SSE
    # Using nested context managers for multiple server connections
    async with MCPServerSse(params=Config.MCP_SERVERS[MCPServerName.WEATHER]) as weather_MCP, \
               MCPServerSse(params=Config.MCP_SERVERS[MCPServerName.NEWS]) as news_MCP:
        
        agent = Agent(
            name="InstaCreator",
            instructions=Prompts.INSTA_AGENT_PROMPT,
            mcp_servers=[weather_MCP, news_MCP],
            model=Config.github_model
        )
        
        # Run the agent with dynamic input from the UI
        print(f"Triggering workflow for: {category_request}")
        result = await Runner.run(
            starting_agent=agent,
            input=category_request
        )
        
        return result.final_output

if __name__ == "__main__":
    test_input = "Create a weather update post for Meerut today."
    final_post = asyncio.run(generate_instagram_post(test_input))
    print("\n--- Final Agent Output ---")
    print(final_post)