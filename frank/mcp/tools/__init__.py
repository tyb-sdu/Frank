"""Register all Frank MCP tools on a FastMCP server."""

from mcp.server.fastmcp import FastMCP

from . import execute, generate, knowledge, query, workflow


def register_all(mcp: FastMCP) -> None:
    query.register(mcp)
    generate.register(mcp)
    execute.register(mcp)
    workflow.register(mcp)
    knowledge.register(mcp)
