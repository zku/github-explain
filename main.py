"""TODO."""

import argparse
import asyncio
import os

from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent.agent import CodeAnalysisAgent
from agent.prompts import project_analysis
from repo.clone import clone_repo

parser = argparse.ArgumentParser("simple_example")
parser.add_argument("--repo", help="Name of the Github repo.", type=str)
console = Console(stderr=True)


async def main():
    """Connects all necessary clients and runs the agent."""
    args = parser.parse_args()
    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
        progress.add_task(f"Downloading {args.repo} for analysis...")
        clone_repo(args.repo)
    console.print("[green] Finished repo download![/green]\n")
    await asyncio.sleep(0.5)

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    async with stdio_client(
        StdioServerParameters(command="uv", args=["run", "./agent/tools/dummy_tool.py"])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            agent = CodeAnalysisAgent(client, mcp_clients=[session])
            await agent.run(project_analysis.TASK_PROMPT)


if __name__ == "__main__":
    asyncio.run(main())
