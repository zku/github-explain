"""TODO."""

import asyncio
import json
import logging
from typing import Any, Callable

import backoff
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from .mcp_utils import create_mcp_client_tool_map

MODEL_ID = "gemini-2.0-flash"
REQUIRE_TOOL_CALL_APPROVAL = False


console = Console(stderr=True)
genai_logger = logging.getLogger("google_genai.types")


def _give_up_for_non_quota_error(error: ClientError) -> bool:
    """Returns true if the genai.errors.ClientError is not about resource exhaustion."""
    return error.code != 429


@backoff.on_exception(
    backoff.expo, ClientError, giveup=_give_up_for_non_quota_error, max_tries=3, max_time=15.0
)
def _call_model(
    client: genai.Client, generation_config: types.GenerationConfig, contents: list[types.Content]
) -> types.GenerateContentResponse:
    """Generate content with the provided configuration and history."""
    return client.models.generate_content(
        model=MODEL_ID,
        config=generation_config,
        contents=contents,
    )


def _format_args(args: dict[str, Any]) -> str:
    """Formats the function call arguments for printing."""
    result = json.dumps(args)
    return result if len(result) < 128 else "{...}"


class CodeAnalysisAgent:
    """Analyzes a codebase using Gemini and the provided tools."""

    def __init__(
        self,
        genai_client: genai.Client,
        mcp_clients: list[ClientSession] = [],
        callables: list[Callable] = [],
    ):
        """Creates a new CodeAnalysisAgent."""
        self._client = genai_client
        self._mcp_clients = mcp_clients
        self._callables = callables + [self._finish]
        self._history: list[types.Content] = []
        self._finished: bool = False
        self._tool_call_count: int = 0
        self._step_count: int = 0
        self._task_result: str = ""

    async def run(self, task_prompt: str):
        """Runs the agent loop until no more function calls are required by the model."""
        self._mcp_client_tools = await asyncio.gather(
            *(create_mcp_client_tool_map(mcp_client) for mcp_client in self._mcp_clients)
        )

        keep_going = await self._step(task_prompt)
        while keep_going and not self._finished:
            keep_going = await self._step("")

        if self._finished:
            console.print("\n\n")
            console.print(
                Panel(
                    self._task_result,
                    title="Task finished",
                    style="yellow",
                    subtitle=f"Steps: {self._step_count}, Tool calls: {self._tool_call_count}",
                )
            )

    def _finish(self, task_result: str | None):
        """Use this tool to signal the task completion."""
        self._finished = True
        self._task_result = task_result or ""
        return "Task complete."

    async def _call_tool(self, name: str, args: dict[str, Any]) -> str | None:
        """Calls the tool with the provided arguments. Asks for permission first."""
        self._tool_call_count += 1
        args_format = _format_args(args)
        if REQUIRE_TOOL_CALL_APPROVAL:
            allow = Prompt.ask(
                (
                    f"[cyan]  >> Allow execution of tool [red]{name}[/red] with "
                    f"arguments [purple]{args_format}[/purple]?[/cyan]"
                ),
                case_sensitive=False,
                choices=["y", "n"],
                default="y",
            )
            if allow != "y":
                return ""

        with Progress(
            SpinnerColumn("arc"),
            TextColumn("{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task(
                f"Calling tool [red]{name}[/red] with arguments [purple]{args_format}[/purple]"
            )
            await asyncio.sleep(0.3)
            for mcp_client, tools in self._mcp_client_tools:
                if name in tools:
                    result: CallToolResult = await mcp_client.call_tool(name, args)
                    return "\n".join(
                        content.text
                        for content in result.content
                        if isinstance(content, TextContent)
                    )
            # Function is not provided by any MCP client. Must be a direct callable.
            for callable in self._callables:
                if getattr(callable, "__name__", repr(callable)) == name:
                    result = callable(**args)
                    if not result:
                        return ""
                    if isinstance(result, dict):
                        return json.dumps(result)
                    if isinstance(result, str):
                        return result
                    return f"{result}"
            raise RuntimeError(f"Attempted to call unknown tool {name}.")

    async def _step(self, prompt: str) -> bool:
        """Performs one model interaction step with function calls."""
        self._step_count += 1
        declarations = [fn for _, tools in self._mcp_client_tools for fn in tools.values()]
        generation_config = types.GenerateContentConfig(
            system_instruction="",
            temperature=1.0,
            tools=[types.Tool(function_declarations=declarations)] + self._callables,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            response_modalities=[types.Modality.TEXT],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.AUTO
                )
            ),
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
            response = _call_model(self._client, generation_config, self._history)
            await asyncio.sleep(1.0)

        # Disable warning logger about function calls and texts existing. We are handling it.
        genai_logger.disabled = True
        text = response.text
        genai_logger.disabled = False

        if text:
            console.print(f"[yellow][ASSISTANT][/yellow] {text}\n")

        if not response.function_calls:
            self._finish(text)
            return False

        for function_call in response.function_calls:
            result = await self._call_tool(function_call.name, function_call.args) or ""
            console.print(
                Panel(
                    result,
                    title=f"Result from function call [purple]{function_call.name}[/purple]",
                    subtitle=_format_args(function_call.args),
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
