"""Serialize Frank dataclasses and results for MCP tool responses."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def to_jsonable(obj: Any) -> Any:
    """Convert Frank objects to JSON-serializable structures."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if is_dataclass(obj):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    if hasattr(obj, "__dict__"):
        return {k: to_jsonable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return str(obj)


def molecule_summary(mol) -> dict:
    return {
        "name": mol.name,
        "name_cn": mol.name_cn,
        "formula": mol.formula,
        "smiles": mol.smiles,
        "charge": mol.charge,
        "spin": mol.spin,
        "multiplicity": mol.multiplicity,
        "atom_count": mol.atom_count,
        "tags": mol.tags,
    }


def intent_summary(intent) -> dict:
    return {
        "molecule": intent.molecule,
        "method": intent.method,
        "basis": intent.basis,
        "calc_type": intent.calc_type,
        "solvent": intent.solvent,
        "n_states": intent.n_states,
        "norb": intent.norb,
        "nelec": intent.nelec,
        "accuracy": intent.accuracy,
        "confidence": intent.confidence,
        "warnings": intent.warnings or [],
    }


def execution_summary(execution) -> dict:
    if execution is None:
        return {}
    return {
        "success": execution.success,
        "return_code": execution.return_code,
        "duration": execution.duration,
        "output_dir": execution.output_dir,
        "error_type": execution.error_type,
        "error_message": execution.error_message,
        "stdout_tail": execution.stdout[-3000:] if execution.stdout else "",
        "stderr_tail": execution.stderr[-2000:] if execution.stderr else "",
        "extracted_results": execution.extracted_results,
    }


def parsed_summary(parsed: dict) -> dict:
    return to_jsonable(parsed)


def workflow_plan_summary(plan) -> dict:
    return {
        "workflow_type": plan.workflow_type,
        "title": plan.title,
        "description": plan.description,
        "method": plan.method,
        "basis": plan.basis,
        "confidence": plan.confidence,
        "is_complex": plan.is_complex,
        "warnings": plan.warnings,
        "tasks": [
            {
                "agent": t.agent,
                "description": t.description,
                "molecule": t.molecule,
                "molecules": t.molecules,
                "method": t.method,
                "basis": t.basis,
                "side": t.side,
            }
            for t in plan.tasks
        ],
    }


def workflow_result_summary(result) -> dict:
    if result is None:
        return {}
    return {
        "success": result.success,
        "summary": result.summary,
        "final_energy": result.final_energy,
        "steps": [
            {
                "name": step.name,
                "description": step.description,
                "status": step.status,
                "parsed": to_jsonable(step.parsed),
                "retry_log": step.retry_log,
                "execution": execution_summary(step.result),
            }
            for step in result.steps
        ],
    }


def orchestrator_result_summary(result) -> dict:
    if result is None:
        return {}
    return {
        "success": result.success,
        "summary": result.summary,
        "warnings": result.warnings,
        "workflow": workflow_result_summary(result.workflow_result),
        "species": [
            {
                "name": s.name,
                "side": s.side,
                "coefficient": s.coefficient,
                "electronic_energy": s.electronic_energy,
                "enthalpy": s.enthalpy,
                "free_energy": s.free_energy,
            }
            for s in result.species_results
        ],
    }
