import os
import asyncio

from agent.agent import CodeAnalysisAgent

from google import genai
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters


async def main():
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    async with stdio_client(
        StdioServerParameters(command="uv", args=["run", "./agent/tools/dummy_tool.py"])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            agent = CodeAnalysisAgent(client, [session])
            await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
