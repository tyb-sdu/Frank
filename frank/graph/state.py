"""LangGraph state schema for Frank."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Literal, Optional, TypedDict


RouteKind = Literal["chat", "explain", "complex", "calculate", "code_only"]


class FrankState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    user_input: str
    entry_route: RouteKind
    route: RouteKind
    execute: bool
    interpret: bool
    require_confirmation: bool
    confirmed: bool

    is_chat: bool
    chat_message: str

    intent: dict[str, Any]
    warnings: list[str]

    script: str
    code_meta: dict[str, Any]

    execution: dict[str, Any]
    parsed: dict[str, Any]
    diagnostics: list[Any]
    interpretation: str
    retry_log: list[Any]
    plain_language: str
    error_diagnosis: str
    execution_success: bool

    plan: dict[str, Any]
    orchestrator_result: dict[str, Any]
    summary: str
    success: bool

    explain_answer: str


def intent_to_dict(intent: Any) -> dict[str, Any]:
    if intent is None:
        return {}
    if is_dataclass(intent):
        return asdict(intent)
    if isinstance(intent, dict):
        return intent
    return {}


def plan_to_dict(plan: Any) -> dict[str, Any]:
    if plan is None:
        return {}
    tasks = []
    for task in getattr(plan, "tasks", []) or []:
        if is_dataclass(task):
            tasks.append(asdict(task))
        elif isinstance(task, dict):
            tasks.append(task)
    return {
        "workflow_type": getattr(plan, "workflow_type", "single"),
        "title": getattr(plan, "title", ""),
        "description": getattr(plan, "description", ""),
        "tasks": tasks,
        "method": getattr(plan, "method", "B3LYP"),
        "basis": getattr(plan, "basis", "6-31g*"),
        "confidence": getattr(plan, "confidence", 0.0),
        "warnings": list(getattr(plan, "warnings", []) or []),
        "is_complex": getattr(plan, "is_complex", False),
    }


def execution_to_dict(execution: Any) -> dict[str, Any]:
    if execution is None:
        return {}
    return {
        "success": getattr(execution, "success", False),
        "stdout": getattr(execution, "stdout", ""),
        "stderr": getattr(execution, "stderr", ""),
        "error_type": getattr(execution, "error_type", None),
        "output_dir": getattr(execution, "output_dir", ""),
        "return_code": getattr(execution, "return_code", None),
        "duration": getattr(execution, "duration", 0.0),
        "error_message": getattr(execution, "error_message", None),
    }


def orchestrator_to_dict(result: Any) -> dict[str, Any]:
    if result is None:
        return {}
    return {
        "success": getattr(result, "success", False),
        "summary": getattr(result, "summary", ""),
        "warnings": list(getattr(result, "warnings", []) or []),
    }
