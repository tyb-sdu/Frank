"""Bridge execution results to CalcStore."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..core.executor import ExecutionResult


def persist_execution_to_store(
    job_id: str,
    execution: "ExecutionResult",
    *,
    update_status: bool = True,
    force: bool = False,
) -> None:
    """Save execution outcome to the database if store is enabled."""
    from ..config import get_store_enabled
    if not force and not get_store_enabled():
        return

    try:
        from .repository import JobRepository
        repo = JobRepository()
        repo.ensure_tables()
        if update_status:
            repo.update_status(
                job_id,
                "completed" if execution.success else "failed",
                error_type=execution.error_type,
                error_message=execution.error_message,
                duration_sec=execution.duration,
                run_dir=execution.output_dir or None,
            )
        if execution.extracted_results or execution.success:
            repo.save_result(job_id, execution.extracted_results or {}, execution.success)
    except Exception:
        pass  # store is optional; never break calculations


def create_job_for_run(
    *,
    molecule_name: str | None,
    method: str | None,
    basis: str | None,
    calc_type: str | None,
    query_text: str | None = None,
    run_dir: str | None = None,
    job_name: str | None = None,
    force: bool = False,
) -> Optional[str]:
    """Create a pending job record before execution; returns job_id or None."""
    from ..config import get_store_enabled
    if not force and not get_store_enabled():
        return None

    try:
        from .repository import JobRepository
        repo = JobRepository()
        repo.ensure_tables()
        return repo.create_job(
            molecule_name=molecule_name,
            method=method,
            basis=basis,
            calc_type=calc_type,
            query_text=query_text,
            run_dir=run_dir,
            job_name=job_name,
            status="running",
        )
    except Exception:
        return None
