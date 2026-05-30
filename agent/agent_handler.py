import asyncio
from pathlib import Path
from agents import Agent, Runner
from agents.mcp import MCPServerSse
from agent.schemas import InstaPost
from shared.config import Config, MCPServerName
from agent.prompts.insta_persona import Prompts

async def generate_instagram_post(user_input: str):
    
    # Connect to the MCP servers over SSE
    # Using nested context managers for multiple server connections
    async with MCPServerSse(params=Config.MCP_SERVERS[MCPServerName.WEATHER]) as weather_MCP, \
               MCPServerSse(params=Config.MCP_SERVERS[MCPServerName.NEWS]) as news_MCP:
        
        agent = Agent(
            name="InstaCreator",
            instructions=Prompts.INSTA_AGENT_PROMPT,
            mcp_servers=[weather_MCP, news_MCP],
            model=Config.github_model,
            output_type=InstaPost
        )
        
        # Run the agent with dynamic input from the UI
        print(f"Triggering workflow for: {user_input}")
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=user_input
            )
            return result.final_output.model_dump()
        except Exception as e:
            print(f"CRITICAL AGENT ERROR: {e}")
            raise e

if __name__ == "__main__":
    test_input = "Give me a general sports update"
    final_post = asyncio.run(generate_instagram_post(test_input))
    print("\n--- Final Agent Output ---")
    print(final_post)