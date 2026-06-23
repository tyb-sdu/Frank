"""MCP knowledge tools — explain and reference."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..context import get_agent


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def frank_explain(question: str) -> dict:
        """Answer computational chemistry questions using Frank's knowledge base.

        Covers methods, basis sets, workflows, and best practices.

        Args:
            question: Question in Chinese or English (e.g. 'B3LYP 适合什么体系?').
        """
        answer = get_agent().explain(question)
        return {"question": question, "answer": answer}

    @mcp.tool()
    def frank_version() -> dict:
        """Return Frank version and MCP server info."""
        from ... import __version__

        return {
            "frank_version": __version__,
            "mcp_server": "frank-mcp",
            "backend": "PySCF",
        }
