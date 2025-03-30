import os
import logging
import glob

from mcp.server.fastmcp import Context, FastMCP


logging.disable(logging.INFO)
mcp = FastMCP("Dummy Server")


@mcp.tool()
def list_files(ctx: Context) -> list[str]:
    """Lists all files in this project."""
    return [
        f"{'[DIR] ' if os.path.isdir(p) else '      '}{p}"
        for p in glob.glob("./**/*", recursive=True)
        if "__pycache__" not in p
    ]


@mcp.tool()
def read_file(ctx: Context, file_path: str) -> str:
    """Read a file."""
    with open(file_path, "r") as f:
        return f.read().encode("utf-8")


if __name__ == "__main__":
    mcp.run()
