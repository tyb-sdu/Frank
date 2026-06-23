"""LangGraph orchestration layer for Frank."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import FrankGraphAgent

__all__ = ["FrankGraphAgent", "build_frank_graph"]


def __getattr__(name: str):
    if name == "FrankGraphAgent":
        from .agent import FrankGraphAgent

        return FrankGraphAgent
    if name == "build_frank_graph":
        from .builder import build_frank_graph

        return build_frank_graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
