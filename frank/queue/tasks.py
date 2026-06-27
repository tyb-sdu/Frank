"""Celery tasks for running PySCF calculations."""

from __future__ import annotations

import json

from .celery_app import celery_app


@celery_app.task(bind=True, name="frank.run_pyscf_job", max_retries=1)
def run_pyscf_job(self, job_id: str, script: str, job_name: str = "frank_job", original_basis: str | None = None):
    """Execute a PySCF script and persist results to CalcStore."""
    from ..core.executor import PySCFExecutor
    from ..store.repository import JobRepository

    repo = JobRepository()
    repo.ensure_tables()
    repo.update_status(job_id, "running", celery_id=self.request.id)

    executor = PySCFExecutor(persist_runs=True)
    execution, retry_log = executor.execute_with_recovery(
        script, job_name, original_basis=original_basis
    )

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

    # Publish progress to Redis for CLI subscribers
    try:
        import redis
        from ..config import get_redis_url
        r = redis.from_url(get_redis_url())
        r.publish(
            f"job:{job_id}:progress",
            json.dumps({
                "status": "completed" if execution.success else "failed",
                "duration": execution.duration,
                "error_type": execution.error_type,
            }),
        )
        r.close()
    except Exception:
        pass

    return {
        "job_id": job_id,
        "success": execution.success,
        "duration": execution.duration,
        "output_dir": execution.output_dir,
        "retry_log": retry_log,
    }


@celery_app.task(name="frank.finalize_workflow")
def finalize_workflow(last_result, workflow_id: str):
    """Mark workflow complete after all steps finish."""
    from ..store.repository import JobRepository

    repo = JobRepository()
    wf = repo.get_workflow(workflow_id)
    if not wf:
        return {"workflow_id": workflow_id, "success": False}
    all_ok = all(step["status"] == "completed" for step in wf["steps"])
    repo.update_workflow_status(workflow_id, "completed" if all_ok else "failed")
    return {"workflow_id": workflow_id, "success": all_ok}


def submit_workflow_jobs(workflow_id: str, job_specs: list[dict]) -> str:
    """Submit a chain of PySCF jobs for a workflow. Returns Celery chain id."""
    from celery import chain

    tasks = []
    for spec in job_specs:
        tasks.append(
            run_pyscf_job.s(
                spec["job_id"],
                spec["script"],
                spec.get("job_name", "frank_job"),
                spec.get("original_basis"),
            )
        )

    workflow_chain = chain(*tasks, finalize_workflow.s(workflow_id))
    result = workflow_chain.apply_async()
    return result.id


def submit_single_job(
    job_id: str,
    script: str,
    job_name: str = "frank_job",
    original_basis: str | None = None,
) -> str:
    """Enqueue a single calculation job. Returns Celery task id."""
    from ..store.repository import JobRepository

    repo = JobRepository()
    repo.update_status(job_id, "queued")
    result = run_pyscf_job.apply_async(
        args=[job_id, script, job_name],
        kwargs={"original_basis": original_basis},
    )
    # In eager mode the task may finish before we return; preserve final status.
    job = repo.get_job(job_id)
    status = job["status"] if job else "queued"
    repo.update_status(job_id, status, celery_id=result.id)
    return result.id
