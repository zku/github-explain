import asyncio
import rich

from google import genai
from google.genai import types
from mcp import ClientSession

from .mcp_utils import convert_mcp_tool_to_genai_function_declaration

MODEL_ID = "gemini-2.0-flash"


class CodeAnalysisAgent:
    def __init__(self, genai_client: genai.Client, mcp_clients: list[ClientSession]):
        self._client = genai_client
        self._mcp_clients = mcp_clients

    async def step(self):
        declarations = await self._create_function_declarations()
        generation_config = types.GenerateContentConfig(
            system_instruction="",
            temperature=1.0,
            tools=[types.Tool(function_declarations=declarations)],
        )
        response = self._client.models.generate_content(
            model=MODEL_ID,
            config=generation_config,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            text="List all files in the current dir. Also reply with 'foo'."
                        )
                    ],
                )
            ],
        )
        rich.inspect(response)

    async def _create_function_declarations(self) -> list[types.FunctionDeclaration]:
        """Creates function declarations for all available tools / functions."""

        async def process_mcp_client(
            mcp_client: ClientSession,
        ) -> types.FunctionDeclaration:
            results: list[types.FunctionDeclaration] = []
            list_tools_result = await mcp_client.list_tools()
            for kind, tools in list_tools_result:
                results.extend(
                    [
                        convert_mcp_tool_to_genai_function_declaration(tool)
                        for tool in tools
                    ]
                    if kind == "tools"
                    else []
                )
            return results

        results = await asyncio.gather(
            *(
                asyncio.create_task(process_mcp_client(mcp_client))
                for mcp_client in self._mcp_clients
            )
        )

        return [r for sr in results for r in sr]
