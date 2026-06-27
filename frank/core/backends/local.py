"""Local subprocess execution via PySCFExecutor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..executor import PySCFExecutor
from .base import BackendResult, ExecutionBackend

if TYPE_CHECKING:
    from ...agent import ParsedIntent


class LocalPySCFBackend(ExecutionBackend):
    mode_name = "local"

    def __init__(self, executor: Optional[PySCFExecutor] = None, timeout: int = 600):
        self.executor = executor or PySCFExecutor(timeout=timeout)

    @property
    def mode(self) -> str:
        return self.mode_name

    def execute(
        self,
        script: str,
        job_name: str,
        intent: ParsedIntent,
        original_basis: Optional[str] = None,
        query_text: str = "",
    ) -> BackendResult:
        execution, retry_log = self.executor.execute_with_recovery(
            script, job_name, original_basis=original_basis
        )
        return BackendResult(
            mode=self.mode,
            success=execution.success,
            execution=execution,
            retry_log=retry_log,
            message="本机 PySCF 计算完成。" if execution.success else "本机计算失败。",
        )
