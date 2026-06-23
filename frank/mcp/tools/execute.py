"""MCP execute tools — run calculations."""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..context import get_agent
from ..serialization import (
    execution_summary,
    intent_summary,
    parsed_summary,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def frank_run_calculation(
        query: str,
        interpret: bool = True,
        timeout: Optional[int] = None,
    ) -> dict:
        """Generate and execute a PySCF calculation from natural language.

        This runs the full pipeline: parse intent → generate code → execute → parse results.

        Args:
            query: Natural language request (e.g. '计算水分子 B3LYP/6-31G* 能量').
            interpret: Include human-readable result interpretation.
            timeout: Override execution timeout in seconds (default from FRANK_TIMEOUT env).
        """
        agent = get_agent()
        if timeout:
            agent.executor.timeout = timeout

        result = agent.run(query, interpret=interpret)

        return {
            "intent": intent_summary(result["intent"]),
            "script": result.get("script", ""),
            "execution": execution_summary(result.get("execution")),
            "parsed": parsed_summary(result.get("parsed", {})),
            "interpretation": result.get("interpretation", ""),
            "plain_language": result.get("plain_language", ""),
            "error_diagnosis": result.get("error_diagnosis", ""),
            "retry_log": result.get("retry_log", []),
            "warnings": result.get("warnings", []),
        }

    @mcp.tool()
    def frank_diagnose_error(
        stderr: str = "",
        stdout: str = "",
        job_context: str = "",
    ) -> dict:
        """Diagnose a failed PySCF calculation from stdout/stderr output.

        Args:
            stderr: Standard error from the failed run.
            stdout: Standard output from the failed run.
            job_context: Optional context (molecule, method, calc type).
        """
        from ...core.error_diagnosis import diagnose_failure, format_diagnosis
        from ...core.diagnostics import DiagnosticsEngine, format_diagnostics

        diag = diagnose_failure(stderr=stderr, stdout=stdout, job_context=job_context)
        diagnostics = DiagnosticsEngine().diagnose_scf_convergence(stdout)

        return {
            "diagnosis": format_diagnosis(diag),
            "likely_cause": diag.likely_cause,
            "suggestions": diag.suggestions,
            "scf_diagnostics": format_diagnostics(diagnostics),
        }
