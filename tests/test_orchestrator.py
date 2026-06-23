"""Tests for Aitomia-inspired orchestrator and knowledge modules."""

import pytest
from frank.orchestrator.planner import WorkflowPlanner, WorkflowPlan
from frank.orchestrator.engine import OrchestratorEngine
from frank.orchestrator.self_correction import SelfCorrectionEngine
from frank.knowledge.base import KnowledgeRetriever, get_knowledge_base
from frank.agent import FrankAgent


class TestWorkflowPlanner:
    @pytest.fixture
    def planner(self):
        return WorkflowPlanner()

    def test_single_calculation_default(self, planner):
        plan = planner.plan("hello world unrelated")
        assert plan.workflow_type == "single"
        assert not plan.is_complex

    def test_reaction_thermo_from_equation(self, planner):
        plan = planner.plan("计算反应能: 2 h2 + o2 -> 2 h2o")
        assert plan.workflow_type == "reaction_thermo"
        assert plan.is_complex
        assert len(plan.tasks) >= 2
        assert plan.confidence >= 0.5

    def test_reaction_thermo_keyword(self, planner):
        plan = planner.plan("计算 Diels-Alder 反应热力学")
        assert plan.workflow_type == "reaction_thermo"
        assert plan.is_complex

    def test_water_formation_template(self, planner):
        plan = planner.plan("计算氢氧反应生成水的反应能")
        assert plan.workflow_type == "reaction_thermo"
        agents = [t.agent for t in plan.tasks]
        assert "opt_freq" in agents
        assert "thermo_analysis" in agents

    def test_tautomer_comparison(self, planner):
        plan = planner.plan("比较 acetaldehyde 互变异构体稳定性")
        assert plan.workflow_type == "tautomer"
        assert plan.is_complex

    def test_conjugation_comparison(self, planner):
        plan = planner.plan("比较 ethene butadiene hexatriene 的共轭和 UV 吸收")
        assert plan.workflow_type == "conjugation"
        assert plan.is_complex

    def test_opt_freq_plan(self, planner):
        plan = planner.plan("对 water 做几何优化和频率计算")
        assert plan.workflow_type == "opt_freq"
        assert plan.is_complex

    def test_method_comparison_plan(self, planner):
        plan = planner.plan("对 benzene 做方法对比")
        assert plan.workflow_type == "method_comparison"


class TestKnowledgeRetriever:
    @pytest.fixture
    def retriever(self):
        return KnowledgeRetriever()

    def test_knowledge_base_not_empty(self):
        kb = get_knowledge_base()
        assert len(kb) > 10

    def test_retrieve_b3lyp(self, retriever):
        chunks = retriever.retrieve("B3LYP 泛函是什么")
        assert len(chunks) > 0
        assert any("b3lyp" in c.topic.lower() or "B3LYP" in c.title for c in chunks)

    def test_retrieve_basis(self, retriever):
        chunks = retriever.retrieve("cc-pVDZ 基组")
        assert len(chunks) > 0

    def test_explain_returns_text(self, retriever):
        answer = retriever.explain("Frank 是什么")
        assert len(answer) > 20
        assert "Frank" in answer or "智能体" in answer

    def test_explain_method_difference(self, retriever):
        answer = retriever.explain("B3LYP 和 MP2 有什么区别")
        assert len(answer) > 30


class TestFrankAgentOrchestration:
    @pytest.fixture
    def agent(self):
        return FrankAgent()

    def test_plan_workflow(self, agent):
        plan = agent.plan_workflow("2 h2 + o2 -> 2 h2o 反应能")
        assert isinstance(plan, WorkflowPlan)
        assert plan.workflow_type == "reaction_thermo"

    def test_is_complex_query(self, agent):
        assert agent.is_complex_query("计算 2 h2 + o2 -> 2 h2o 的反应能")
        assert not agent.is_complex_query("计算水分子的能量")

    def test_explain(self, agent):
        answer = agent.explain("什么是自校正机制")
        assert "自校正" in answer or "虚频" in answer or "self" in answer.lower()

    def test_run_autonomous_non_complex(self, agent):
        result = agent.run_autonomous("计算水分子能量")
        assert result["success"] is False
        assert result["plan"].workflow_type == "single"


class TestSelfCorrectionEngine:
    def test_inject_tight_convergence(self):
        engine = SelfCorrectionEngine()
        script = "mf = scf.RHF(mol)\nmf.kernel()"
        patched = engine._inject_tight_convergence(script)
        assert "conv_tol" in patched
        assert "max_cycle" in patched
