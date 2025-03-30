import os
import logging

from mcp.server.fastmcp import Context, FastMCP


logging.disable(logging.INFO)
mcp = FastMCP("Dummy Server")


@mcp.tool()
def list_files(ctx: Context) -> list[str]:
    """Lists files in the current directory."""
    return os.listdir("./")


if __name__ == "__main__":
    mcp.run()
