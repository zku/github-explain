"""TODO."""

import asyncio
import json
import logging
from typing import Any

from google import genai
from google.genai import types
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from .mcp_utils import create_mcp_client_tool_map

MODEL_ID = "gemini-2.0-flash"


console = Console(stderr=True)
genai_logger = logging.getLogger("google_genai.types")


class CodeAnalysisAgent:
    """Analyzes a codebase using Gemini and the provided tools."""

    def __init__(self, genai_client: genai.Client, mcp_clients: list[ClientSession]):
        """Creates a new CodeAnalysisAgent."""
        self._client = genai_client
        self._mcp_clients = mcp_clients
        self._history: list[types.Content] = []

    async def run(self, task_prompt: str):
        """Runs the agent loop until no more function calls are required by the model."""
        self._mcp_client_tools = await asyncio.gather(
            *(create_mcp_client_tool_map(mcp_client) for mcp_client in self._mcp_clients)
        )

        keep_going = await self._step(task_prompt)
        while keep_going:
            keep_going = await self._step("")

    async def _call_tool(self, name: str, args: dict[str, Any]) -> str | None:
        """Calls the tool with the provided arguments. Asks for permission first."""
        allow = Prompt.ask(
            (
                f"Allow execution of tool [red]{name}[/red] with "
                f"arguments [purple]{json.dumps(args)}[/purple]?"
            ),
            choices=["y", "n"],
            default="y",
        )
        if allow != "y":
            return ""

        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            for mcp_client, tools in self._mcp_client_tools:
                if name in tools:
                    progress.add_task(f"Calling tool {name} with arguments {json.dumps(args)}")
                    result: CallToolResult = await mcp_client.call_tool(name, args)
                    return "\n".join(
                        content.text
                        for content in result.content
                        if isinstance(content, TextContent)
                    )

    async def _step(self, prompt: str) -> bool:
        """Performs one model interaction step with function calls."""
        declarations = [fn for _, tools in self._mcp_client_tools for fn in tools.values()]
        generation_config = types.GenerateContentConfig(
            system_instruction="",
            temperature=1.0,
            tools=[types.Tool(function_declarations=declarations)],
        )

        if prompt != "":
            console.print(f"[blue][USER][/blue] {prompt}\n")
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
        genai_logger.disabled = True
        if text := response.text:
            console.print(f"[yellow][ASSISTANT][/yellow] {text}\n")
        genai_logger.disabled = False

        if not response.function_calls:
            return False

        for function_call in response.function_calls:
            result = await self._call_tool(function_call.name, function_call.args) or ""

            console.print(
                Panel(
                    result,
                    title=f"Result from function call [purple]{function_call.name}[/purple]",
                    subtitle=json.dumps(function_call.args),
                    style="green",
                )
            )
            self._history.append(
                types.Content(
                    role="model",
                    parts=[types.Part(function_call=function_call)],
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
        return True
