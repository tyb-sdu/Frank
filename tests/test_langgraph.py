"""Tests for LangGraph orchestration layer."""

import pytest

langgraph = pytest.importorskip("langgraph")

from frank.graph import FrankGraphAgent, build_frank_graph
from frank.agent import FrankAgent


class TestFrankGraph:
    @pytest.fixture
    def graph_agent(self):
        return FrankGraphAgent()

    def test_graph_compiles(self, graph_agent):
        assert graph_agent._graph is not None

    def test_build_from_agent(self):
        agent = FrankAgent()
        graph = build_frank_graph(agent)
        assert graph is not None

    def test_chat_route(self, graph_agent):
        result = graph_agent.process_request("你好")
        assert result["is_chat"] is True
        assert result["chat_message"]

    def test_code_only_route(self, graph_agent):
        result = graph_agent.process_request("用 B3LYP 计算水分子能量")
        assert result["is_chat"] is not True
        assert "h2o" in result["script"].lower() or "water" in result["script"].lower()

    def test_explain_route(self, graph_agent):
        result = graph_agent.invoke("explain what is B3LYP", execute=False)
        assert "answer" in result
        assert result["answer"]

    def test_complex_workflow_interrupt(self, graph_agent):
        result = graph_agent.run_autonomous(
            "计算 2 h2 + o2 -> 2 h2o 的反应能",
            require_confirmation=True,
        )
        assert result.get("awaiting_confirmation") is True
        assert result.get("thread_id")
        plan = result.get("plan")
        assert plan is not None
        assert plan.is_complex

    def test_non_complex_autonomous_skips_confirm(self, graph_agent):
        result = graph_agent.run_autonomous(
            "计算水分子能量",
            require_confirmation=True,
        )
        assert result.get("awaiting_confirmation") is not True
        assert result.get("success") is False
        assert result.get("plan").workflow_type == "single"

    def test_agent_factory_defaults_to_graph(self):
        from frank.cli.agent_factory import create_agent

        agent = create_agent()
        assert isinstance(agent, FrankGraphAgent)
