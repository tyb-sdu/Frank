"""Shared Frank agent instance for MCP tool handlers."""

from __future__ import annotations

import os
from typing import Optional, Union

from ..agent import FrankAgent

_agent: Optional[Union[FrankAgent, "FrankGraphAgent"]] = None
_force_classic: Optional[bool] = None


def use_langgraph() -> bool:
    """Return True when LangGraph orchestration should be used."""
    global _force_classic
    if _force_classic is not None:
        return not _force_classic

    env = os.environ.get("FRANK_USE_CLASSIC", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return False

    try:
        import langgraph  # noqa: F401
        return True
    except ImportError:
        return False


def get_agent() -> Union[FrankAgent, "FrankGraphAgent"]:
    """Return a process-wide agent, LangGraph by default when available."""
    global _agent
    if _agent is None:
        work_dir = os.environ.get("FRANK_WORK_DIR")
        timeout = int(os.environ.get("FRANK_TIMEOUT", "600"))
        if use_langgraph():
            from ..graph import FrankGraphAgent

            _agent = FrankGraphAgent(work_dir=work_dir, timeout=timeout)
        else:
            _agent = FrankAgent(work_dir=work_dir, timeout=timeout)
    return _agent


def reset_agent(force_classic: Optional[bool] = None) -> None:
    """Reset the shared agent (mainly for tests)."""
    global _agent, _force_classic
    _agent = None
    _force_classic = force_classic


def set_use_classic(classic: bool) -> None:
    """Force classic or LangGraph mode and reset the cached agent."""
    global _force_classic
    _force_classic = classic
    reset_agent(force_classic=classic)
