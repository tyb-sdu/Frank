"""Tests for Frank MCP tool handlers."""

import pytest
from mcp.server.fastmcp import FastMCP

from frank.mcp.context import reset_agent
from frank.mcp.server import create_server
from frank.mcp.tools import query, generate, knowledge, workflow


@pytest.fixture(autouse=True)
def _reset_agent():
    reset_agent()
    yield
    reset_agent()


def _get_tool_fn(mcp: FastMCP, name: str):
    return mcp._tool_manager._tools[name].fn


class TestMCPServer:
    def test_create_server_registers_20_tools(self):
        server = create_server()
        names = {t.name for t in server._tool_manager.list_tools()}
        assert len(names) == 20
        assert "frank_run_calculation" in names
        assert "frank_run_autonomous" in names


class TestQueryTools:
    def test_list_molecules(self):
        mcp = FastMCP("test")
        query.register(mcp)
        fn = _get_tool_fn(mcp, "frank_list_molecules")
        result = fn(search="h2o", limit=5)
        assert result["count"] >= 1
        assert any(m["name"] == "h2o" for m in result["molecules"])

    def test_get_molecule(self):
        mcp = FastMCP("test")
        query.register(mcp)
        fn = _get_tool_fn(mcp, "frank_get_molecule")
        result = fn(name="h2o")
        assert result["formula"] == "H2O"
        assert "xyz" in result

    def test_list_methods(self):
        mcp = FastMCP("test")
        query.register(mcp)
        fn = _get_tool_fn(mcp, "frank_list_methods")
        result = fn()
        assert "dft_functionals" in result
        assert "post_hf" in result
        assert any(m["name"] == "MP2" for m in result["post_hf"])

    def test_recommend_basis(self):
        mcp = FastMCP("test")
        query.register(mcp)
        fn = _get_tool_fn(mcp, "frank_recommend_basis")
        result = fn(method="B3LYP", calc_type="energy")
        assert "recommended" in result
        assert result["recommended"]

    def test_list_solvents(self):
        mcp = FastMCP("test")
        query.register(mcp)
        fn = _get_tool_fn(mcp, "frank_list_solvents")
        result = fn()
        assert "solvents" in result
        assert any(s["name"] == "water" for s in result["solvents"])


class TestGenerateTools:
    def test_parse_intent(self):
        mcp = FastMCP("test")
        generate.register(mcp)
        fn = _get_tool_fn(mcp, "frank_parse_intent")
        result = fn(query="计算水分子 B3LYP/6-31G* 单点能")
        assert result["intent"]["molecule"] == "h2o"
        assert result["intent"]["method"] == "B3LYP"

    def test_generate_code_from_query(self):
        mcp = FastMCP("test")
        generate.register(mcp)
        fn = _get_tool_fn(mcp, "frank_generate_code")
        result = fn(query="计算水分子 B3LYP/6-31G* 单点能")
        assert result["success"] is True
        assert "pyscf" in result["script"].lower()
        assert result["intent"]["calc_type"] == "energy"

    def test_generate_code_structured(self):
        mcp = FastMCP("test")
        generate.register(mcp)
        fn = _get_tool_fn(mcp, "frank_generate_code")
        result = fn(molecule="h2o", method="HF", basis="sto-3g", calc_type="energy")
        assert result["success"] is True
        assert "HF" in result["script"] or "hf" in result["script"].lower()


class TestKnowledgeTools:
    def test_version(self):
        mcp = FastMCP("test")
        knowledge.register(mcp)
        fn = _get_tool_fn(mcp, "frank_version")
        result = fn()
        assert result["frank_version"] == "0.1.0"
        assert result["backend"] == "PySCF"

    def test_explain(self):
        mcp = FastMCP("test")
        knowledge.register(mcp)
        fn = _get_tool_fn(mcp, "frank_explain")
        result = fn(question="What is B3LYP?")
        assert "answer" in result
        assert len(result["answer"]) > 0


class TestWorkflowTools:
    def test_is_complex_query_simple(self):
        mcp = FastMCP("test")
        workflow.register(mcp)
        fn = _get_tool_fn(mcp, "frank_is_complex_query")
        result = fn(query="计算水分子 B3LYP 能量")
        assert result["is_complex"] is False

    def test_is_complex_query_reaction(self):
        mcp = FastMCP("test")
        workflow.register(mcp)
        fn = _get_tool_fn(mcp, "frank_is_complex_query")
        result = fn(query="计算 2H2 + O2 -> 2H2O 的反应能")
        assert result["is_complex"] is True

    def test_plan_workflow(self):
        mcp = FastMCP("test")
        workflow.register(mcp)
        fn = _get_tool_fn(mcp, "frank_plan_workflow")
        result = fn(query="计算 2H2 + O2 -> 2H2O 的反应能")
        assert result["workflow_type"] != "single"
        assert len(result["tasks"]) > 0
