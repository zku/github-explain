"""TODO."""

import json

from google.genai.types import FunctionDeclaration, Schema, Type
from mcp import ClientSession
from mcp.types import Tool

_type_replacements = {
    "object": Type.OBJECT,
    "string": Type.STRING,
    "number": Type.NUMBER,
    "boolean": Type.BOOLEAN,
    "array": Type.ARRAY,
    "integer": Type.INTEGER,
}


def convert_mcp_tool_to_genai_function_declaration(
    tool: Tool,
) -> FunctionDeclaration:
    """Converts an MCP tool description/schema to Google's function declaration schema."""
    mcp_schema_json = json.dumps(tool.inputSchema)
    google_schema_json = mcp_schema_json
    for old, new in _type_replacements.items():
        google_schema_json = google_schema_json.replace(old, new)
    parameters = json.loads(google_schema_json)

    declaration = FunctionDeclaration(
        name=tool.name, description=tool.description, parameters=parameters
    )

    # MCP uses type=object even for functions that do not take any arguments.
    # The Google genai API returns an error for type=object with empty parameters.
    # To solve this, we just inject an unused, nullable parameter of a primitive type.
    if declaration.parameters.type == Type.OBJECT and not declaration.parameters.properties:
        declaration.parameters.properties["unused"] = Schema(type=Type.INTEGER, nullable=True)

    return declaration


async def create_mcp_client_tool_map(
    mcp_client: ClientSession,
) -> tuple[ClientSession, dict[str, FunctionDeclaration]]:
    """Returns the provided client and a dict mapping tool name to function declaration."""
    list_tools_result = await mcp_client.list_tools()
    tool_mapping = {}
    for kind, tools in list_tools_result:
        if kind != "tools":
            continue
        tool_mapping.update(
            {tool.name: convert_mcp_tool_to_genai_function_declaration(tool) for tool in tools}
        )
    return mcp_client, tool_mapping
