"""
Export calculation results to JSON and CSV formats.

Supports both single-calculation results and workflow results.
"""

import json
import csv
import os
from typing import Any


def _make_serializable(obj: Any) -> Any:
    """Convert non-serializable objects to serializable types."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _make_serializable(v) for k, v in obj.items()}
    return str(obj)


def export_to_json(result: dict, filepath: str) -> None:
    """Export a result dictionary to a JSON file.

    Args:
        result: The result dictionary from agent.run() or workflow.
        filepath: Path to the output JSON file.
    """
    serializable = {}
    for key, value in result.items():
        if key == "code":
            serializable["code_title"] = value.title if value else ""
            serializable["script"] = result.get("script", "")
        elif key == "execution":
            if value:
                serializable["execution"] = {
                    "success": value.success,
                    "duration": value.duration,
                    "error_type": value.error_type,
                    "error_message": value.error_message,
                    "stdout": value.stdout[-5000:] if value.stdout else "",
                    "stderr": value.stderr[-5000:] if value.stderr else "",
                }
        elif key == "parsed":
            if value:
                serializable["parsed"] = {}
                for k, v in value.items():
                    serializable["parsed"][k] = _make_serializable(v)
        elif key == "diagnostics":
            if value:
                serializable["diagnostics"] = [
                    {
                        "level": d.level,
                        "category": d.category,
                        "title": d.title,
                        "description": d.description,
                        "suggestions": d.suggestions,
                    }
                    for d in value
                ]
        elif key == "interpretation":
            serializable[key] = value
        elif key == "intent":
            if value:
                serializable["intent"] = {
                    "molecule": value.molecule,
                    "method": value.method,
                    "basis": value.basis,
                    "calc_type": value.calc_type,
                    "solvent": value.solvent,
                    "confidence": value.confidence,
                }
        else:
            serializable[key] = _make_serializable(value)

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False, default=str)


def export_to_csv(result: dict, filepath: str) -> None:
    """Export result data to a CSV file.

    Flattens key result metrics into a single row for tabular analysis.
    Useful for method comparisons and batch calculations.

    Args:
        result: The result dictionary.
        filepath: Path to the output CSV file.
    """
    rows = []

    # Handle workflow results (list of steps)
    steps = result.get("steps", [])
    if steps:
        for step in steps:
            row = {
                "name": step.get("name", ""),
                "description": step.get("description", ""),
                "status": step.get("status", ""),
            }
            parsed = step.get("parsed", {})
            for k, v in parsed.items():
                if hasattr(v, "__dict__"):
                    for attr, attr_val in v.__dict__.items():
                        if isinstance(attr_val, (int, float, str, bool)) or attr_val is None:
                            row[f"{k}_{attr}"] = attr_val
                else:
                    row[k] = str(v)
            rows.append(row)
    else:
        # Handle single calculation result
        row = {}
        parsed = result.get("parsed", {})
        for k, v in parsed.items():
            if hasattr(v, "__dict__"):
                for attr, attr_val in v.__dict__.items():
                    if isinstance(attr_val, (int, float, str, bool)) or attr_val is None:
                        row[f"{k}_{attr}"] = attr_val
            else:
                row[k] = str(v)
        if result.get("execution"):
            row["success"] = result["execution"].success
            row["duration"] = result["execution"].duration
        if result.get("intent"):
            row["method"] = result["intent"].method
            row["basis"] = result["intent"].basis
            row["molecule"] = result["intent"].molecule
        rows.append(row)

    if not rows:
        return

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
