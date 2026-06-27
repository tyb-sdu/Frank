"""Serialize orchestrator workflow plans for database storage."""

from __future__ import annotations

from dataclasses import asdict

from ..orchestrator.planner import WorkflowPlan, WorkflowTask


def plan_to_dict(plan: WorkflowPlan) -> dict:
    return {
        "workflow_type": plan.workflow_type,
        "title": plan.title,
        "description": plan.description,
        "method": plan.method,
        "basis": plan.basis,
        "confidence": plan.confidence,
        "warnings": plan.warnings,
        "tasks": [asdict(t) for t in plan.tasks],
    }


def plan_from_dict(data: dict) -> WorkflowPlan:
    tasks = [WorkflowTask(**t) for t in data.get("tasks", [])]
    return WorkflowPlan(
        workflow_type=data.get("workflow_type", "single"),
        title=data.get("title", ""),
        description=data.get("description", ""),
        tasks=tasks,
        method=data.get("method", "B3LYP"),
        basis=data.get("basis", "6-31g*"),
        confidence=data.get("confidence", 0.0),
        warnings=data.get("warnings", []),
    )
