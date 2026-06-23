"""LangGraph node functions — thin wrappers around FrankAgent capabilities."""

from __future__ import annotations

import glob
from typing import TYPE_CHECKING, Any

from ..agent import ParsedIntent
from ..core.executor_common import classify_error
from ..core.error_diagnosis import diagnose_failure, format_diagnosis
from ..molecules.database import get_molecule
from .state import (
    execution_to_dict,
    intent_to_dict,
    orchestrator_to_dict,
    plan_to_dict,
)

if TYPE_CHECKING:
    from ..agent import FrankAgent


def classify_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    entry_route = state.get("entry_route")
    if entry_route:
        return {"route": entry_route}

    text = state["user_input"]
    text_lower = text.lower().strip()

    if not agent._is_chemistry_query(text):
        return {"route": "chat", "is_chat": True}

    explain_keywords = ["explain", "解释", "什么是", "what is", "how does", "原理"]
    if any(kw in text_lower for kw in explain_keywords):
        return {"route": "explain"}

    if agent.is_complex_query(text):
        return {"route": "complex"}

    if state.get("execute") is False:
        return {"route": "code_only"}
    return {"route": "calculate"}


def chat_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "is_chat": True,
        "chat_message": agent._chat_reply(state["user_input"]),
        "success": True,
    }


def explain_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    answer = agent.explain(state["user_input"])
    return {
        "explain_answer": answer,
        "success": True,
    }


def parse_intent_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    intent = agent.parse_intent(state["user_input"])
    return {
        "intent": intent_to_dict(intent),
        "warnings": list(intent.warnings),
    }


def generate_code_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    intent_data = state.get("intent") or {}
    intent = ParsedIntent(**{k: v for k, v in intent_data.items() if k in ParsedIntent.__dataclass_fields__})
    warnings = list(state.get("warnings") or [])

    if not intent.molecule:
        return {"script": "", "warnings": warnings}

    try:
        code = agent.generate_code(intent)
        agent.session.update(intent)
        return {
            "script": code.to_script(),
            "_code_obj": code,
            "code_meta": {
                "title": code.title,
                "description": code.description,
                "calc_type": intent.calc_type,
                "method": intent.method,
                "basis": intent.basis,
            },
            "warnings": warnings,
        }
    except Exception as exc:
        warnings.append(f"Code generation failed: {exc}")
        return {"script": "", "warnings": warnings}


def execute_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    intent_data = state.get("intent") or {}
    intent = ParsedIntent(**{k: v for k, v in intent_data.items() if k in ParsedIntent.__dataclass_fields__})
    script = state.get("script") or ""
    warnings = list(state.get("warnings") or [])

    if not script or not intent.molecule:
        return {
            "execution": {},
            "execution_success": False,
            "warnings": warnings,
        }

    mol = get_molecule(intent.molecule)
    job_name = f"{mol.name}_{intent.method or 'b3lyp'}".lower()
    execution, retry_log = agent.executor.execute_with_recovery(
        script, job_name, original_basis=intent.basis
    )

    parsed: dict[str, Any] = {}
    if execution.success:
        parsed = agent.parser.parse_from_stdout(execution.stdout)
        for log_file in glob.glob(f"{execution.output_dir}/*.log"):
            parsed.update(agent.parser.parse_from_file(log_file))

    return {
        "execution": execution_to_dict(execution),
        "parsed": parsed,
        "retry_log": retry_log,
        "execution_success": execution.success,
        "warnings": warnings,
        "_execution_obj": execution,
        "_intent_obj": intent,
        "_mol_obj": mol,
    }


def interpret_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    if not state.get("interpret", True):
        return {"success": True}

    parsed = state.get("parsed") or {}
    intent_data = state.get("intent") or {}
    method = intent_data.get("method") or "HF"
    mol_name = intent_data.get("molecule") or ""

    interpretation = ""
    if parsed:
        try:
            mol = get_molecule(mol_name)
            mol_label = mol.name_cn
        except KeyError:
            mol_label = mol_name
        interpretation = agent.interpreter.interpret(parsed, method=method, mol_name=mol_label)

    return {
        "interpretation": interpretation,
        "success": bool(state.get("execution_success")),
    }


def diagnose_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    execution = state.get("_execution_obj")
    intent_data = state.get("intent") or {}
    if execution is None:
        return {"success": False}

    diagnostics = []
    if execution.error_type:
        diagnostics.extend(agent.diagnostics.diagnose_scf_convergence(execution.stdout))
        _, _, plain_language = classify_error(execution.stderr, execution.stdout)
        diag = diagnose_failure(
            stderr=execution.stderr,
            stdout=execution.stdout,
            output_dir=execution.output_dir,
            job_context=(
                f"{intent_data.get('molecule')} "
                f"{intent_data.get('method')}/{intent_data.get('basis')} "
                f"{intent_data.get('calc_type')}"
            ),
        )
        error_diagnosis = format_diagnosis(diag)
        if diag.likely_cause and not plain_language:
            plain_language = diag.likely_cause
        return {
            "diagnostics": diagnostics,
            "plain_language": plain_language,
            "error_diagnosis": error_diagnosis,
            "success": False,
        }

    return {"diagnostics": diagnostics, "success": False}


def plan_workflow_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    plan = state.get("_plan_obj") or agent.plan_workflow(state["user_input"])
    return {
        "plan": plan_to_dict(plan),
        "warnings": list(plan.warnings),
        "_plan_obj": plan,
    }


def confirm_complex_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    if state.get("confirmed"):
        return {}

    if not state.get("require_confirmation", True):
        return {"confirmed": True}

    plan_obj = state.get("_plan_obj")
    if plan_obj is not None and not plan_obj.is_complex:
        return {"confirmed": True}

    from langgraph.types import interrupt

    plan = state.get("plan") or {}
    response = interrupt(
        {
            "type": "confirm_complex_workflow",
            "plan": plan,
            "message": (
                "Complex workflow detected. Confirm execution? "
                "This may take several minutes."
            ),
        }
    )
    if not response:
        return {
            "confirmed": False,
            "success": False,
            "summary": "Workflow cancelled — confirmation not granted.",
            "warnings": list(state.get("warnings") or [])
            + ["Execution cancelled — confirmation not granted."],
        }
    return {"confirmed": True}


def orchestrate_node(agent: FrankAgent, state: dict[str, Any]) -> dict[str, Any]:
    from ..orchestrator.engine import OrchestratorEngine

    plan = state.get("_plan_obj") or agent.plan_workflow(state["user_input"])
    if not plan.is_complex:
        warnings = list(state.get("warnings") or [])
        warnings.extend(plan.warnings)
        warnings.append(
            "Query does not require a complex workflow; use 'run' for single calculations."
        )
        return {
            "plan": plan_to_dict(plan),
            "orchestrator_result": {},
            "summary": "",
            "success": False,
            "warnings": warnings,
        }

    orchestrator = OrchestratorEngine(
        executor=agent.executor,
        timeout=agent.executor.timeout,
    )
    progress_callback = getattr(agent, "_progress_callback", None)
    result = orchestrator.execute(plan, progress_callback=progress_callback)
    return {
        "plan": plan_to_dict(plan),
        "orchestrator_result": orchestrator_to_dict(result),
        "_orchestrator_obj": result,
        "summary": result.summary,
        "success": result.success,
        "warnings": list(state.get("warnings") or []) + list(result.warnings),
    }
