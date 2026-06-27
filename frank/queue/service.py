"""High-level service for submitting jobs via store + queue."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..agent import FrankAgent
from ..orchestrator.planner import WorkflowPlanner
from ..store.repository import JobRepository
from ..store.serialization import plan_to_dict
from .tasks import submit_single_job, submit_workflow_jobs


@dataclass
class SubmitResult:
    job_id: str | None = None
    workflow_id: str | None = None
    celery_id: str | None = None
    is_workflow: bool = False
    message: str = ""


class JobSubmissionService:
    """Prepare and enqueue Frank calculations."""

    def __init__(self, agent: FrankAgent | None = None, timeout: int = 600):
        self.agent = agent or FrankAgent(timeout=timeout)
        self.repo = JobRepository()
        self.planner = WorkflowPlanner()

    def submit(self, query_text: str) -> SubmitResult:
        self.repo.ensure_tables()

        # Try workflow planning first
        plan = self.planner.plan(query_text)
        if plan.is_complex and plan.tasks:
            return self._submit_workflow(query_text, plan)

        return self._submit_single(query_text)

    def _submit_single(self, query_text: str) -> SubmitResult:
        intent = self.agent.parse_intent(query_text)
        if not intent.molecule:
            return SubmitResult(message="Could not parse molecule from query.")

        code = self.agent.generate_code(intent)
        script = code.to_script()
        mol_name = intent.molecule
        job_name = f"{mol_name}_{intent.method or 'b3lyp'}".lower()

        job_id = self.repo.create_job(
            molecule_name=mol_name,
            method=intent.method,
            basis=intent.basis,
            calc_type=intent.calc_type,
            query_text=query_text,
            job_name=job_name,
            status="pending",
        )

        celery_id = submit_single_job(
            job_id, script, job_name, original_basis=intent.basis
        )
        return SubmitResult(
            job_id=job_id,
            celery_id=celery_id,
            message=f"Job queued: {job_id}",
        )

    def _submit_workflow(self, query_text: str, plan) -> SubmitResult:
        workflow_id = self.repo.create_workflow(
            title=plan.title,
            workflow_type=plan.workflow_type,
            plan_json=plan_to_dict(plan),
            query_text=query_text,
            status="queued",
        )

        job_specs = []
        for i, task in enumerate(plan.tasks):
            if task.agent not in ("opt_freq", "conformer_search"):
                continue
            mol = task.molecule or (task.molecules[0] if task.molecules else None)
            if not mol:
                continue

            from ..agent import ParsedIntent
            intent = ParsedIntent(
                molecule=mol,
                method=task.method or plan.method,
                basis=task.basis or plan.basis,
                calc_type="geometry",
            )
            code = self.agent.generate_code(intent)
            script = code.to_script()
            job_name = f"{mol}_{task.method or plan.method}".lower()

            job_id = self.repo.create_job(
                molecule_name=mol,
                method=task.method or plan.method,
                basis=task.basis or plan.basis,
                calc_type="opt_freq",
                query_text=query_text,
                job_name=job_name,
                status="pending",
            )
            self.repo.link_workflow_job(workflow_id, job_id, i)
            job_specs.append({
                "job_id": job_id,
                "script": script,
                "job_name": job_name,
                "original_basis": task.basis or plan.basis,
            })

        if not job_specs:
            self.repo.update_workflow_status(workflow_id, "failed")
            return SubmitResult(
                workflow_id=workflow_id,
                is_workflow=True,
                message="Workflow planned but no executable tasks found.",
            )

        celery_id = submit_workflow_jobs(workflow_id, job_specs)
        return SubmitResult(
            workflow_id=workflow_id,
            job_id=job_specs[0]["job_id"] if job_specs else None,
            celery_id=celery_id,
            is_workflow=True,
            message=f"Workflow queued: {workflow_id} ({len(job_specs)} steps)",
        )


def get_job_status(job_id: str) -> dict | None:
    """Return job status dict for CLI display."""
    return JobRepository().get_job(job_id)


def get_workflow_status(workflow_id: str) -> dict | None:
    """Return workflow status with step details."""
    return JobRepository().get_workflow(workflow_id)
