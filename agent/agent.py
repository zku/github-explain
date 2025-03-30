import asyncio
import json
import logging

from google import genai
from google.genai import types
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent
from typing import Any
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
from rich.panel import Panel

from .mcp_utils import create_mcp_client_tool_map
from .prompts import TASK_PROMPT


MODEL_ID = "gemini-2.0-flash"


console = Console(stderr=True)


class CodeAnalysisAgent:
    def __init__(self, genai_client: genai.Client, mcp_clients: list[ClientSession]):
        self._client = genai_client
        self._mcp_clients = mcp_clients
        self._history: list[types.Content] = []

    async def run(self):
        self._mcp_client_tools = await asyncio.gather(
            *(
                create_mcp_client_tool_map(mcp_client)
                for mcp_client in self._mcp_clients
            )
        )
        await self._step(TASK_PROMPT)

    async def _call_tool(self, name: str, args: dict[str, Any]) -> str | None:
        console.print(
            f"[red] Allow execution of tool {name} with arguments {json.dumps(args)}[/red]? (y/n)"
        )
        ans = input(">> ")
        if ans != "y":
            return ""
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            for mcp_client, tools in self._mcp_client_tools:
                if name in tools:
                    progress.add_task(
                        f"Calling tool {name} with arguments {json.dumps(args)}"
                    )
                    result: CallToolResult = await mcp_client.call_tool(name, args)
                    return "\n".join(
                        content.text
                        for content in result.content
                        if isinstance(content, TextContent)
                    )

    async def _step(self, prompt: str):
        declarations = [
            fn for _, tools in self._mcp_client_tools for fn in tools.values()
        ]
        generation_config = types.GenerateContentConfig(
            system_instruction="",
            temperature=1.0,
            tools=[types.Tool(function_declarations=declarations)],
        )

        if prompt != "":
            console.print(f"[blue][USER][/blue] {prompt}")
            self._history.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=prompt)],
                )
            )

        with Progress(
            SpinnerColumn(),
            TextColumn("[purple]{task.description}[/purple]"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task("Thinking...")
            response = self._client.models.generate_content(
                model=MODEL_ID,
                config=generation_config,
                contents=self._history,
            )

        # Disable warning logger about function calls and texts existing. We are handling it.
        logging.getLogger("google_genai.types").disabled = True
        if response.text:
            console.print(f"[yellow][ASSISTANT][/yellow] {response.text}")
        logging.getLogger("google_genai.types").disabled = False
        if response.function_calls:
            for i, function_call in enumerate(response.function_calls):
                result = (
                    await self._call_tool(function_call.name, function_call.args) or ""
                )

                console.print(
                    Panel(
                        result,
                        title=f"Result from function call [purple]{function_call.name}[/purple]",
                        style="green",
                    )
                )
                self._history.append(
                    types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                function_call=function_call,
                            )
                        ],
                    )
                )
                self._history.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    id=function_call.id,
                                    name=function_call.name,
                                    response={"output": result},
                                )
                            )
                        ],
                    )
                )

            # We had function calls. Keep going.
            return await self._step("")
