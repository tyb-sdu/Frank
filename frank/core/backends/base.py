"""Execution backend abstraction for Frank calculations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from ..executor import ExecutionResult

if TYPE_CHECKING:
    from ...agent import ParsedIntent


@dataclass
class BackendResult:
    """Unified result from any execution backend."""

    mode: str
    success: bool
    execution: Optional[ExecutionResult] = None
    export_dir: Optional[str] = None
    export_files: list[str] = field(default_factory=list)
    job_id: Optional[str] = None
    celery_id: Optional[str] = None
    retry_log: list[str] = field(default_factory=list)
    message: str = ""


class ExecutionBackend(ABC):
    """Run, export, or queue a generated PySCF script."""

    @property
    @abstractmethod
    def mode(self) -> str:
        ...

    @abstractmethod
    def execute(
        self,
        script: str,
        job_name: str,
        intent: ParsedIntent,
        original_basis: Optional[str] = None,
        query_text: str = "",
    ) -> BackendResult:
        ...
