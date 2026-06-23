"""MCP workflow tools — multi-step and autonomous calculations."""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..context import get_agent
from ..serialization import (
    orchestrator_result_summary,
    workflow_plan_summary,
    workflow_result_summary,
)


WORKFLOW_TYPES = [
    "opt_freq",
    "method_comparison",
    "basis_convergence",
    "pes_scan",
    "solvation",
]


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def frank_plan_workflow(query: str) -> dict:
        """Plan a multi-step computational workflow without executing it.

        Use for complex requests like reaction thermochemistry, tautomer comparison,
        conformer search, or method/basis convergence studies.

        Args:
            query: Natural language workflow description.
        """
        plan = get_agent().plan_workflow(query)
        return workflow_plan_summary(plan)

    @mcp.tool()
    def frank_run_workflow(
        workflow_type: str,
        molecule: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        methods: Optional[str] = None,
        basis_sets: Optional[str] = None,
        solvent: str = "water",
        scan_type: str = "bond",
        atoms: str = "0,1",
        n_points: int = 11,
        range_start: float = 0.8,
        range_end: float = 2.0,
        timeout: Optional[int] = None,
    ) -> dict:
        """Run a predefined multi-step workflow.

        workflow_type options:
          - opt_freq: geometry optimization + frequency
          - method_comparison: compare multiple methods
          - basis_convergence: test basis set convergence
          - pes_scan: potential energy surface scan
          - solvation: solvation free energy

        Args:
            methods: Comma-separated methods for method_comparison (e.g. 'HF,B3LYP,MP2').
            basis_sets: Comma-separated basis sets for basis_convergence.
            atoms: Comma-separated atom indices for pes_scan.
        """
        if workflow_type not in WORKFLOW_TYPES:
            return {
                "success": False,
                "message": f"Unknown workflow_type '{workflow_type}'. Valid: {WORKFLOW_TYPES}",
            }

        agent = get_agent()
        if timeout:
            agent.executor.timeout = timeout

        kwargs = {}
        if methods:
            kwargs["methods"] = [m.strip() for m in methods.split(",")]
        if basis_sets:
            kwargs["basis_sets"] = [b.strip() for b in basis_sets.split(",")]
        kwargs["solvent"] = solvent
        kwargs["scan_type"] = scan_type
        kwargs["atoms"] = atoms
        kwargs["n_points"] = n_points
        kwargs["range_start"] = range_start
        kwargs["range_end"] = range_end

        result = agent.run_workflow(
            molecule=molecule,
            workflow_type=workflow_type,
            method=method,
            basis=basis,
            **kwargs,
        )
        summary = workflow_result_summary(result)
        summary["success"] = result.success if result else False
        return summary

    @mcp.tool()
    def frank_run_autonomous(
        query: str,
        timeout: Optional[int] = None,
        require_confirmation: bool = True,
        confirmed: bool = False,
        thread_id: Optional[str] = None,
    ) -> dict:
        """Plan and autonomously execute a complex multi-step workflow.

        Handles reaction thermochemistry, tautomer/conformer comparison,
        conjugation studies, and other multi-molecule orchestrated tasks.

        When require_confirmation is True, the first call returns
        awaiting_confirmation=True and a thread_id. Resume with
        confirmed=True and the same thread_id to execute.

        Args:
            query: Complex natural language request.
            timeout: Override execution timeout in seconds.
            require_confirmation: Pause for confirmation before execution.
            confirmed: Resume a paused workflow after confirmation.
            thread_id: Thread id from a prior awaiting_confirmation response.
        """
        agent = get_agent()
        if timeout:
            agent.executor.timeout = timeout

        outcome = agent.run_autonomous(
            query,
            require_confirmation=require_confirmation,
            confirmed=confirmed,
            thread_id=thread_id,
        )
        response = {
            "plan": workflow_plan_summary(outcome["plan"]) if outcome.get("plan") else None,
            "success": outcome.get("success", False),
            "summary": outcome.get("summary", ""),
            "warnings": outcome.get("warnings", []),
            "result": orchestrator_result_summary(outcome.get("result")),
            "awaiting_confirmation": outcome.get("awaiting_confirmation", False),
            "thread_id": outcome.get("thread_id"),
        }
        return response

    @mcp.tool()
    def frank_is_complex_query(query: str) -> dict:
        """Check whether a query requires multi-step orchestration vs a single calculation."""
        agent = get_agent()
        is_complex = agent.is_complex_query(query)
        plan = agent.plan_workflow(query)
        return {
            "is_complex": is_complex,
            "workflow_type": plan.workflow_type,
            "title": plan.title,
            "task_count": len(plan.tasks),
            "confidence": plan.confidence,
        }
