"""LLM-based error diagnosis — Aitomia-inspired failure analysis from logs."""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from typing import Optional

from ..config import get_api_key
from .executor_common import classify_error


@dataclass
class ErrorDiagnosis:
    likely_cause: str
    suggestions: list[str] = field(default_factory=list)
    technical_summary: str = ""
    source: str = "rule-based"  # rule-based | llm


def _collect_log_context(output_dir: str, stderr: str, stdout: str, max_chars: int = 4000) -> str:
    """Aggregate traceback and log files from the working directory."""
    parts = []
    if stderr:
        parts.append("=== STDERR ===\n" + stderr[-1500:])
    if stdout:
        parts.append("=== STDOUT (tail) ===\n" + stdout[-1500:])

    if output_dir and os.path.isdir(output_dir):
        for pattern in ("*.log", "*.err", "*.out"):
            for path in sorted(glob.glob(os.path.join(output_dir, pattern))):
                try:
                    content = open(path, encoding="utf-8", errors="ignore").read()
                    if content.strip():
                        parts.append(f"=== {os.path.basename(path)} ===\n{content[-800:]}")
                except OSError:
                    pass

    combined = "\n\n".join(parts)
    return combined[-max_chars:] if len(combined) > max_chars else combined


def _rule_based_diagnosis(error_type: str, message: str, plain: str) -> ErrorDiagnosis:
    suggestions_map = {
        "scf_convergence": [
            "Increase mf.max_cycle to 200",
            "Add damping: mf.damp = 0.5",
            "Verify the molecular geometry",
        ],
        "memory": [
            "Use density fitting: mf = mf.density_fit()",
            "Switch to a smaller basis set",
        ],
        "geometry": [
            "Check for atoms that are too close",
            "Re-run geometry optimization",
        ],
        "linear_dep": [
            "Remove diffuse functions from the basis set",
            "Use 6-31G* instead of 6-31++G**",
        ],
    }
    return ErrorDiagnosis(
        likely_cause=plain or message,
        suggestions=suggestions_map.get(error_type, ["Review input parameters and retry"]),
        technical_summary=message,
        source="rule-based",
    )


def diagnose_failure(
    stderr: str = "",
    stdout: str = "",
    output_dir: str = "",
    job_context: str = "",
) -> ErrorDiagnosis:
    """Diagnose a failed calculation using rules + optional LLM analysis."""
    error_type, message, plain = classify_error(stderr, stdout)
    context = _collect_log_context(output_dir, stderr, stdout)

    llm_result = _diagnose_with_llm(context, error_type, job_context)
    if llm_result:
        return llm_result

    return _rule_based_diagnosis(error_type, message, plain)


def _diagnose_with_llm(
    context: str,
    error_type: str,
    job_context: str,
) -> Optional[ErrorDiagnosis]:
    if not get_api_key() or not context.strip():
        return None
    try:
        from openai import OpenAI
        from ..llm import get_base_url, get_model_name

        client = OpenAI(api_key=get_api_key(), base_url=get_base_url())
        response = client.chat.completions.create(
            model=get_model_name(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a computational chemistry error analyst (like Aitomia). "
                        "Given calculation logs/tracebacks, identify the likely cause and "
                        "suggest 2-4 concrete corrective actions. "
                        "Respond in JSON: {\"cause\": \"...\", \"suggestions\": [\"...\"], "
                        "\"technical\": \"...\"}. Use the same language as the job context."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Error type (rule-based): {error_type}\n"
                        f"Job context: {job_context or 'PySCF calculation'}\n\n"
                        f"Logs:\n{context}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        import json
        data = json.loads(response.choices[0].message.content)
        return ErrorDiagnosis(
            likely_cause=data.get("cause", ""),
            suggestions=data.get("suggestions", []),
            technical_summary=data.get("technical", ""),
            source="llm",
        )
    except Exception:
        return None


def format_diagnosis(diag: ErrorDiagnosis) -> str:
    lines = ["\n--- Error Diagnosis ---", f"Likely cause: {diag.likely_cause}"]
    if diag.suggestions:
        lines.append("Suggested actions:")
        for i, s in enumerate(diag.suggestions, 1):
            lines.append(f"  {i}. {s}")
    if diag.technical_summary and diag.technical_summary != diag.likely_cause:
        lines.append(f"Technical: {diag.technical_summary}")
    lines.append(f"(Source: {diag.source})")
    return "\n".join(lines)
