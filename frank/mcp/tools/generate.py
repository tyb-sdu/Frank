"""MCP generate tools — intent parsing and code generation."""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from ...agent import ParsedIntent
from ..context import get_agent
from ..serialization import intent_summary


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def frank_parse_intent(query: str, use_session: bool = True) -> dict:
        """Parse natural language into structured calculation intent.

        Example queries:
          - '计算水分子 B3LYP/6-31G* 单点能'
          - 'Optimize benzene geometry with MP2/cc-pVDZ'
          - '苯的 TDDFT 激发态 6 个'

        Args:
            query: Natural language calculation request.
            use_session: Reuse molecule/method from previous queries in this session.
        """
        agent = get_agent()
        intent = agent.parse_intent(query, use_session=use_session)
        return {
            "intent": intent_summary(intent),
            "is_complex": agent.is_complex_query(query),
        }

    @mcp.tool()
    def frank_generate_code(
        query: Optional[str] = None,
        molecule: Optional[str] = None,
        method: Optional[str] = None,
        basis: Optional[str] = None,
        calc_type: Optional[str] = None,
        solvent: Optional[str] = None,
        n_states: Optional[int] = None,
        norb: Optional[int] = None,
        nelec: Optional[int] = None,
    ) -> dict:
        """Generate executable PySCF Python code without running it.

        Provide either a natural language `query`, or structured parameters.
        Structured parameters override parsed intent fields.

        calc_type options: energy, geometry, frequency, excited, casscf, nbo, solvation.
        """
        agent = get_agent()

        if query:
            intent = agent.parse_intent(query)
        else:
            intent = ParsedIntent(
                molecule=molecule,
                method=method,
                basis=basis,
                calc_type=calc_type,
                solvent=solvent,
                n_states=n_states,
                norb=norb,
                nelec=nelec,
            )
            agent._infer_defaults(intent)

        overrides = {}
        for field in ("molecule", "method", "basis", "calc_type", "solvent", "n_states", "norb", "nelec"):
            val = locals()[field]
            if val is not None:
                overrides[field] = val
        if overrides:
            intent = agent.adjust_intent(intent, overrides)

        if not intent.molecule:
            return {
                "success": False,
                "intent": intent_summary(intent),
                "script": "",
                "message": "No molecule specified. Use frank_search_pubchem or frank_list_molecules first.",
            }

        try:
            code = agent.generate_code(intent)
            agent.session.update(intent)
        except Exception as exc:
            return {
                "success": False,
                "intent": intent_summary(intent),
                "script": "",
                "message": str(exc),
            }

        return {
            "success": True,
            "intent": intent_summary(intent),
            "title": code.title,
            "script": code.to_script(),
            "blocks": [
                {"order": b.order, "section": b.section, "description": b.description}
                for b in sorted(code.blocks, key=lambda x: x.order)
            ],
        }

    @mcp.tool()
    def frank_get_help() -> str:
        """Return Frank usage help text covering methods, basis sets, and workflows."""
        return get_agent().get_help()
