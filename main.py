"""TODO."""

import asyncio
import os

from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent.agent import CodeAnalysisAgent
from agent.prompts import add_docstrings


async def main():
    """Connects all necessary clients and runs the agent."""
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    async with stdio_client(
        StdioServerParameters(command="uv", args=["run", "./agent/tools/dummy_tool.py"])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            agent = CodeAnalysisAgent(client, [session])
            await agent.run(add_docstrings.TASK_PROMPT)


if __name__ == "__main__":
    asyncio.run(main())
