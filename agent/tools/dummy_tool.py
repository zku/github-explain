"""TODO."""

import glob
import logging
import os

from mcp.server.fastmcp import Context, FastMCP

logging.disable(logging.INFO)
mcp = FastMCP("Dummy Server")


def _list_allowed_files() -> list[str]:
    """Returns a list of allowed files in this project."""
    return [
        p
        for p in glob.glob("./**/*", recursive=True)
        if "__pycache__" not in p and "README" not in p
    ]


@mcp.tool()
def list_files(ctx: Context) -> list[str]:
    """Lists all files in this project."""
    return [f"{'[DIR] ' if os.path.isdir(p) else '      '}{p}" for p in _list_allowed_files()]


@mcp.tool()
def read_file(ctx: Context, file_path: str) -> str:
    """Read a file. Only the exact file paths provided by the list_files tools are allowed."""
    allowed_files = set(_list_allowed_files())
    if file_path not in allowed_files and f"./{file_path}" not in allowed_files:
        return (
            f"ERROR: Unknown file {file_path}. "
            "Only the exact file paths provided by the list_files tools are allowed."
        )
    with open(file_path, "r") as f:
        return f.read().encode("utf-8")


if __name__ == "__main__":
    mcp.run()
