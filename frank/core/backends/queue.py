"""Celery queue backend — async job submission via CalcStore."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .base import BackendResult, ExecutionBackend

if TYPE_CHECKING:
    from ...agent import ParsedIntent


class QueueBackend(ExecutionBackend):
    mode_name = "queue"

    def __init__(self, timeout: int = 600):
        self.timeout = timeout

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
        try:
            from ...store.repository import JobRepository
            from ...queue.tasks import submit_single_job
        except ImportError as exc:
            return BackendResult(
                mode=self.mode,
                success=False,
                message=f"队列后端不可用: {exc}",
            )

        repo = JobRepository()
        repo.ensure_tables()

        job_id = repo.create_job(
            molecule_name=intent.molecule or "",
            method=intent.method,
            basis=intent.basis,
            calc_type=intent.calc_type,
            query_text=query_text,
            job_name=job_name,
            status="pending",
        )

        try:
            celery_id = submit_single_job(
                job_id, script, job_name, original_basis=original_basis
            )
        except Exception as exc:
            repo.update_status(job_id, "failed", error_message=str(exc))
            return BackendResult(
                mode=self.mode,
                success=False,
                job_id=job_id,
                message=f"提交队列失败: {exc}。请确认 Redis 已启动 (docker compose up -d)。",
            )

        return BackendResult(
            mode=self.mode,
            success=True,
            job_id=job_id,
            celery_id=celery_id,
            message=f"任务已提交队列，Job ID: {job_id}。使用 frank status {job_id[:8]} 查看进度。",
        )
