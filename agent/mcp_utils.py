import json

from mcp.types import Tool
from google.genai.types import Type, FunctionDeclaration, Schema
from mcp import ClientSession

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
    # Convert the input MCP schema to the genai schema by renaming the types.
    mcp_schema_json = json.dumps(tool.inputSchema)
    google_schema_json = mcp_schema_json
    for old, new in _type_replacements.items():
        google_schema_json = google_schema_json.replace(old, new)
    parameters = json.loads(google_schema_json)

    declaration = FunctionDeclaration(
        name=tool.name, description=tool.description, parameters=parameters
    )

    # The API does not tolerate declarations of type OBJECT without parameters.
    # Inject an unused, nullable parameter if necessary.
    if (
        declaration.parameters.type == Type.OBJECT
        and not declaration.parameters.properties
    ):
        declaration.parameters.properties["unused"] = Schema(
            type=Type.INTEGER, nullable=True
        )

    return declaration


async def create_mcp_client_tool_map(
    mcp_client: ClientSession,
) -> tuple[ClientSession, dict[str, FunctionDeclaration]]:
    list_tools_result = await mcp_client.list_tools()
    tool_mapping = {}
    for kind, tools in list_tools_result:
        if kind != "tools":
            continue
        tool_mapping.update(
            {
                tool.name: convert_mcp_tool_to_genai_function_declaration(tool)
                for tool in tools
            }
        )
    return mcp_client, tool_mapping
