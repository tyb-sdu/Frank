"""
模板引擎测试。
"""

import pytest
from frank.templates.pyscf_templates import PySCFTemplateEngine
from frank.templates.base import GeneratedCode


class TestPySCFTemplateEngine:
    """PySCF 模板引擎测试类"""

    @pytest.fixture
    def engine(self):
        return PySCFTemplateEngine()

    def test_generate_scf(self, engine):
        """测试 SCF 代码生成"""
        code = engine.generate_scf("h2o", "HF", "6-31g*")
        assert isinstance(code, GeneratedCode)
        assert "scf" in code.to_script().lower()
        assert "mol" in code.to_script()

    def test_generate_dft(self, engine):
        """测试 DFT 代码生成"""
        code = engine.generate_dft("h2o", "B3LYP", "6-31g*")
        assert isinstance(code, GeneratedCode)
        assert "b3lyp" in code.to_script().lower()
        assert "dft" in code.to_script().lower()

    def test_generate_mp2(self, engine):
        """测试 MP2 代码生成"""
        code = engine.generate_mp2("h2o", "cc-pvdz")
        assert isinstance(code, GeneratedCode)
        assert "mp2" in code.to_script().lower()

    def test_generate_ccsd(self, engine):
        """测试 CCSD 代码生成"""
        code = engine.generate_ccsd("h2o", "cc-pvdz")
        assert isinstance(code, GeneratedCode)
        assert "ccsd" in code.to_script().lower()

    def test_generate_ccsd_t(self, engine):
        """测试 CCSD(T) 代码生成"""
        code = engine.generate_ccsd_t("h2o", "cc-pvdz")
        assert isinstance(code, GeneratedCode)
        assert "ccsd" in code.to_script().lower()
        assert "ccsd_t" in code.to_script().lower()

    def test_generate_tddft(self, engine):
        """测试 TDDFT 代码生成"""
        code = engine.generate_tddft("c6h6", "B3LYP", "6-31g*", 6)
        assert isinstance(code, GeneratedCode)
        assert "tddft" in code.to_script().lower() or "TDHF" in code.to_script()

    def test_generate_casscf(self, engine):
        """测试 CASSCF 代码生成"""
        code = engine.generate_casscf("n2", "cc-pvdz", 6, 6)
        assert isinstance(code, GeneratedCode)
        assert "casscf" in code.to_script().lower()

    def test_generate_geometry_opt(self, engine):
        """测试几何优化代码生成"""
        code = engine.generate_geometry_opt("h2o", "B3LYP", "6-31g*")
        assert isinstance(code, GeneratedCode)
        assert "optimize" in code.to_script().lower()

    def test_generate_frequency(self, engine):
        """测试频率计算代码生成"""
        code = engine.generate_frequency("h2o", "B3LYP", "6-31g*")
        assert isinstance(code, GeneratedCode)
        assert "hessian" in code.to_script().lower() or "freq" in code.to_script().lower()

    def test_generate_custom(self, engine):
        """测试自定义代码生成"""
        code = engine.generate_custom("h2o", "B3LYP", "6-31g*", "energy")
        assert isinstance(code, GeneratedCode)

    def test_generate_custom_with_solvent(self, engine):
        """测试带溶剂化的代码生成"""
        code = engine.generate_custom("h2o", "B3LYP", "6-31g*", "energy", solvent="water")
        assert isinstance(code, GeneratedCode)
        assert "solvent" in code.to_script().lower() or "pcm" in code.to_script().lower()

    def test_code_has_imports(self, engine):
        """测试代码包含导入"""
        code = engine.generate_dft("h2o", "B3LYP", "6-31g*")
        script = code.to_script()
        assert "from pyscf import" in script

    def test_code_has_molecule(self, engine):
        """测试代码包含分子定义"""
        code = engine.generate_dft("h2o", "B3LYP", "6-31g*")
        script = code.to_script()
        assert "gto.Mole()" in script
        assert "mol.atom" in script

    def test_code_has_basis(self, engine):
        """测试代码包含基组设置"""
        code = engine.generate_dft("h2o", "B3LYP", "cc-pvdz")
        script = code.to_script()
        assert "cc-pvdz" in script.lower() or "cc-pVDZ" in script

    def test_different_molecules(self, engine):
        """测试不同分子的代码生成"""
        molecules = ["h2o", "nh3", "ch4", "co2", "c6h6"]
        for mol_name in molecules:
            code = engine.generate_dft(mol_name, "B3LYP", "6-31g*")
            assert isinstance(code, GeneratedCode)
            assert len(code.to_script()) > 100

    def test_different_functionals(self, engine):
        """测试不同泛函的代码生成"""
        functionals = ["B3LYP", "PBE", "PBE0", "M06-2X", "wB97X-D"]
        for func in functionals:
            code = engine.generate_dft("h2o", func, "6-31g*")
            assert isinstance(code, GeneratedCode)

    def test_different_basis_sets(self, engine):
        """测试不同基组的代码生成"""
        basis_sets = ["6-31g*", "cc-pvdz", "cc-pvtz", "def2-tzvp"]
        for basis in basis_sets:
            code = engine.generate_dft("h2o", "B3LYP", basis)
            assert isinstance(code, GeneratedCode)

    def test_run_instructions(self, engine):
        """测试运行说明"""
        code = engine.generate_dft("h2o", "B3LYP", "6-31g*")
        assert code.run_instructions
        assert "pip install pyscf" in code.run_instructions

    def test_title_and_description(self, engine):
        """测试标题和描述"""
        code = engine.generate_dft("h2o", "B3LYP", "6-31g*")
        assert code.title
        assert code.description
        assert "水" in code.title or "H2O" in code.title


class TestGeneratedCode:
    """生成代码测试类"""

    def test_to_script(self):
        """测试脚本组装"""
        from frank.templates.base import CodeBlock
        code = GeneratedCode(
            title="测试",
            description="测试代码",
            blocks=[
                CodeBlock(section="imports", code="import os", order=0),
                CodeBlock(section="calculation", code="print('hello')", order=10),
            ],
        )
        script = code.to_script()
        assert "import os" in script
        assert "print('hello')" in script

    def test_to_script_with_comments(self):
        """测试带注释的脚本"""
        from frank.templates.base import CodeBlock
        code = GeneratedCode(
            title="测试",
            description="测试代码",
            blocks=[
                CodeBlock(section="imports", code="import os", order=0, description="导入模块"),
            ],
        )
        script = code.to_script(include_comments=True)
        assert "# 导入模块" in script

    def test_to_script_section_order(self):
        """测试区域排序"""
        from frank.templates.base import CodeBlock
        code = GeneratedCode(
            title="测试",
            description="测试代码",
            blocks=[
                CodeBlock(section="calculation", code="calc()", order=10),
                CodeBlock(section="imports", code="import os", order=0),
            ],
        )
        script = code.to_script()
        # imports 应该在 calculation 之前
        assert script.index("import os") < script.index("calc()")
