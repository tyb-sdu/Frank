"""Tests for Aitomia-style benchmark tasks and new optimization modules."""

import pytest
from frank.orchestrator.planner import WorkflowPlanner
from frank.orchestrator.stoichiometry import solve_stoichiometry
from frank.molecules.database import get_molecule, MOLECULE_ALIASES
from frank.molecules.conformers import generate_conformers
from frank.core.spectrum_reference import (
    get_builtin_reference, compare_with_reference, format_comparison_report,
)
from frank.core.workdir import RunDirectory, should_persist_runs
from frank.knowledge.base import KnowledgeRetriever


class TestBenchmarkPlanner:
    """Aitomia Table 1 style workflow planning tests."""

    @pytest.fixture
    def planner(self):
        return WorkflowPlanner()

    def test_proton_affinity_template(self, planner):
        plan = planner.plan("计算氨的质子亲和能")
        assert plan.workflow_type == "reaction_thermo"
        assert plan.is_complex
        molecules = [t.molecule for t in plan.tasks if t.molecule]
        assert "nh3" in molecules
        assert "h+" in molecules or "nh4+" in molecules

    def test_conjugation_series(self, planner):
        plan = planner.plan("比较 ethene butadiene hexatriene 共轭长度对 UV 吸收的影响")
        assert plan.workflow_type == "conjugation"
        assert plan.is_complex

    def test_conformer_workflow(self, planner):
        plan = planner.plan("对 water 进行构象搜索")
        assert plan.workflow_type == "conformer"
        assert plan.is_complex
        assert any(t.agent == "conformer_search" for t in plan.tasks)

    def test_tautomer_with_correct_names(self, planner):
        plan = planner.plan("比较 acetaldehyde 互变异构体稳定性")
        assert plan.workflow_type == "tautomer"
        molecules = [t.molecule for t in plan.tasks if t.molecule]
        assert "ch3cho" in molecules or "ethenol" in molecules


class TestMoleculeAliases:
    def test_acetaldehyde_alias(self):
        mol = get_molecule("acetaldehyde")
        assert mol.name == "ch3cho"

    def test_h_plus_ion(self):
        mol = get_molecule("h+")
        assert mol.charge == 1
        assert mol.atom_count == 1

    def test_ethenol_exists(self):
        mol = get_molecule("ethenol")
        assert "O" in mol.formula


class TestStoichiometryProtonation:
    def test_nh3_protonation(self):
        result = solve_stoichiometry(["nh3", "h+"], ["nh4+"])
        assert result.balanced
        assert ("nh3", 1) in result.reactants
        assert ("h+", 1) in result.reactants
        assert ("nh4+", 1) in result.products


class TestConformerSearch:
    def test_generate_conformers_ethanol(self):
        result = generate_conformers("CCO", "ethanol", n_conformers=3)
        assert not result.error
        assert len(result.conformers) >= 1
        assert result.best is not None


class TestSpectrumReference:
    def test_builtin_water(self):
        ref = get_builtin_reference("h2o")
        assert ref is not None
        assert len(ref.peaks) >= 2

    def test_compare_frequencies(self):
        ref = get_builtin_reference("h2o")
        comparison = compare_with_reference([3650, 1600, 500], ref)
        assert comparison["n_matches"] >= 1
        report = format_comparison_report(comparison)
        assert "参考来源" in report


class TestRunDirectory:
    def test_create_run_dir(self, tmp_path):
        rd = RunDirectory.create("test_job", base_dir=str(tmp_path))
        assert rd.path.exists()
        rd.write_script("print('hello')")
        assert (rd.path / f"{rd.job_name}.py").exists()

    def test_should_persist_runs(self):
        assert isinstance(should_persist_runs(), bool)


class TestAdaptiveRAG:
    def test_retrieve_conformer_knowledge(self):
        retriever = KnowledgeRetriever()
        chunks = retriever.retrieve("构象搜索工作流", top_k=3)
        assert len(chunks) >= 1

    def test_retrieve_stoichiometry(self):
        retriever = KnowledgeRetriever()
        chunks = retriever.retrieve("化学计量 null space", top_k=3)
        assert any("stoichiometry" in c.topic or "化学计量" in c.title for c in chunks)
