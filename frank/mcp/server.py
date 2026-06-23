"""Frank MCP server entry point."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .. import __version__
from .tools import register_all


def create_server() -> FastMCP:
    """Create and configure the Frank FastMCP server."""
    mcp = FastMCP(
        name="frank",
        instructions=(
            "Frank computational chemistry MCP server. "
            "Generates and runs PySCF quantum chemistry calculations. "
            "Use query tools to explore molecules/methods, "
            "generate tools for code, execute tools to run calculations, "
            "and workflow tools for multi-step tasks."
        ),
    )
    register_all(mcp)
    return mcp


def main() -> None:
    """Run the Frank MCP server over stdio (Cursor default transport)."""
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
