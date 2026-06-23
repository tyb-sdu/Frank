"""CLI agent factory — LangGraph by default, classic opt-out."""

from __future__ import annotations

import os
from typing import Optional, Union

from ..agent import FrankAgent


def create_agent(
    timeout: int = 600,
    work_dir: Optional[str] = None,
    classic: bool = False,
) -> Union[FrankAgent, "FrankGraphAgent"]:
    """Create FrankAgent or FrankGraphAgent based on flags and environment."""
    use_classic = classic or os.environ.get("FRANK_USE_CLASSIC", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if use_classic:
        return FrankAgent(work_dir=work_dir, timeout=timeout)

    try:
        from ..graph import FrankGraphAgent

        return FrankGraphAgent(work_dir=work_dir, timeout=timeout)
    except ImportError:
        return FrankAgent(work_dir=work_dir, timeout=timeout)
