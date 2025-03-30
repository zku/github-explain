import asyncio
import json

from google import genai
from google.genai import types
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent
from typing import Any
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel

from .mcp_utils import create_mcp_client_tool_map


MODEL_ID = "gemini-2.0-flash"


# 1. Define Tokyo Night-like colors
tokyo_colors = {
    "bg": "#1a1b26",
    "fg": "#c0caf5",
    "comment": "#565f89",
    "keyword": "#bb9af7",
    "string": "#9ece6a",
    "number": "#ff9e64",
    "function": "#7aa2f7",
    "variable": "#c0caf5",  # Can use fg or another color like #7dcfff
    "error": "#f7768e",
    "warning": "#ff9e64",  # Using orange for warnings
    "info": "#7aa2f7",  # Using blue for info
    "debug": "#565f89",  # Using comment color for debug
    "purple": "#bb9af7",
    "green": "#9ece6a",
    "blue": "#7aa2f7",
    "orange": "#ff9e64",
    "red": "#f7768e",
}

# 2. Create the Rich Theme dictionary
# We map style names (some custom, some overriding Rich defaults) to style definitions
tokyo_night_theme_dict = {
    "default": f"{tokyo_colors['fg']}",  # Default text color
    # Custom styles for markup
    "keyword": f"bold {tokyo_colors['keyword']}",
    "function": f"{tokyo_colors['function']}",
    "variable": f"{tokyo_colors['variable']}",
    "comment": f"italic {tokyo_colors['comment']}",
    "string": f"{tokyo_colors['string']}",
    "number": f"{tokyo_colors['number']}",
    "operator": f"{tokyo_colors['fg']}",  # Default for operators like +,-,=
    "error": f"bold {tokyo_colors['error']}",
    "warning": f"{tokyo_colors['warning']}",
    "info": f"{tokyo_colors['info']}",
    "debug": f"{tokyo_colors['debug']}",
    "repr.str": f"{tokyo_colors['string']}",  # Style for strings in rich.print()
    "repr.number": f"{tokyo_colors['number']}",  # Style for numbers in rich.print()
    "repr.bool_true": f"bold {tokyo_colors['keyword']}",  # Style for True
    "repr.bool_false": f"bold {tokyo_colors['keyword']}",  # Style for False
    "repr.none": f"italic {tokyo_colors['comment']}",  # Style for None
    "repr.url": f"underline {tokyo_colors['blue']}",  # Style for URLs
    # Logging styles
    "log.level.warning": f"{tokyo_colors['warning']}",
    "log.level.error": f"bold {tokyo_colors['error']}",
    "log.level.critical": f"bold reverse {tokyo_colors['error']}",
    "log.level.info": f"{tokyo_colors['info']}",
    "log.level.debug": f"{tokyo_colors['debug']}",
    # Traceback styles (can be customized further)
    "traceback.exc_type": f"bold {tokyo_colors['error']}",
    "traceback.exc_value": f"{tokyo_colors['error']}",
    "traceback.filename": f"{tokyo_colors['green']}",
    "traceback.lineno": f"bold {tokyo_colors['number']}",
    "traceback.name": f"{tokyo_colors['function']}",
    # You can add many more Rich default styles here if needed
}
tokyo_night_theme = Theme(tokyo_night_theme_dict)

console = Console(theme=tokyo_night_theme, stderr=True)


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
        await self._step(
            "List all files in the current directory. Once you have all the file names, concatenate them all together as 1 string and let me know what it is!"
        )

    async def _call_tool(self, name: str, args: dict[str, Any]) -> str | None:
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
                    await asyncio.sleep(1.0)
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

        response = self._client.models.generate_content(
            model=MODEL_ID,
            config=generation_config,
            contents=self._history,
        )

        if response.function_calls:
            assert len(response.function_calls) == 1, (
                "Cannot handle multiple function calls in one step."
            )
            result = (
                await self._call_tool(
                    response.function_calls[0].name, response.function_calls[0].args
                )
                or ""
            )

            console.print(
                Panel(
                    result,
                    title=f"Result from function call [purple]{response.function_calls[0].name}[/purple]",
                    style="green",
                )
            )
            self._history.append(response.candidates[0].content)
            self._history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            function_response=types.FunctionResponse(
                                id=response.function_calls[0].id,
                                name=response.function_calls[0].name,
                                response={"output": result},
                            )
                        )
                    ],
                )
            )
            return await self._step("")
        else:
            console.print(f"[yellow][ASSISTANT][/yellow] {response.text}")
