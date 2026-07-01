"""
智能体测试。
"""

import pytest
from frank.agent import FrankAgent, ParsedIntent


class TestFrankAgent:
    """Frank 智能体测试类"""

    @pytest.fixture
    def agent(self):
        return FrankAgent()

    def test_parse_molecule(self, agent):
        """测试分子识别"""
        intent = agent.parse_intent("计算水分子的能量")
        assert intent.molecule == "h2o"

    def test_parse_method(self, agent):
        """测试方法识别"""
        intent = agent.parse_intent("用 B3LYP 计算")
        assert intent.method == "B3LYP"

    def test_parse_scf_method_variants(self, agent):
        """测试显式 SCF 方法识别"""
        assert agent.parse_intent("用 RHF 计算水分子").method == "RHF"
        assert agent.parse_intent("用 UHF 计算氧气").method == "UHF"
        assert agent.parse_intent("用 ROHF 计算水分子").method == "ROHF"

    def test_parse_basis(self, agent):
        """测试基组识别"""
        intent = agent.parse_intent("使用 6-31G* 基组")
        assert intent.basis == "6-31g*"

    def test_parse_extended_basis_names(self, agent):
        """测试更多基组写法识别"""
        assert agent.parse_intent("用 def2-QZVP 计算水分子").basis == "def2-qzvp"
        assert agent.parse_intent("用 6-311+G(d,p) 计算水分子").basis == "6-311+g(d,p)"

    def test_parse_calc_type(self, agent):
        """测试计算类型识别"""
        # 几何优化
        intent = agent.parse_intent("几何优化")
        assert intent.calc_type == "geometry"

        # 频率
        intent = agent.parse_intent("频率计算")
        assert intent.calc_type == "frequency"

        # 激发态
        intent = agent.parse_intent("激发态")
        assert intent.calc_type == "excited"

    def test_parse_solvent(self, agent):
        """测试溶剂识别"""
        intent = agent.parse_intent("在水中的溶剂化")
        assert intent.solvent == "water"

    def test_parse_solvent_context_case_insensitive(self, agent):
        """测试英文溶剂上下文大小写不敏感"""
        intent = agent.parse_intent("Calculate h2o with Solvent DMSO")
        assert intent.solvent == "dmso"

    def test_parse_accuracy_affects_recommended_basis(self, agent):
        """测试精度意图影响默认基组推荐"""
        intent = agent.parse_intent("高精度计算水分子能量")
        assert intent.accuracy == "high"
        assert intent.basis == "cc-pvtz"

    def test_parse_n_states(self, agent):
        """测试激发态数识别"""
        intent = agent.parse_intent("计算6个激发态")
        assert intent.n_states == 6

    def test_parse_complex_request(self, agent):
        """测试复杂请求解析"""
        intent = agent.parse_intent("计算水分子在 B3LYP/6-31G* 水平的几何优化")
        assert intent.molecule == "h2o"
        assert intent.method == "B3LYP"
        assert intent.basis == "6-31g*"
        assert intent.calc_type == "geometry"

    def test_parse_ccsd_t(self, agent):
        """测试 CCSD(T) 识别"""
        intent = agent.parse_intent("用 CCSD(T) 计算")
        assert intent.method == "CCSD(T)"

    def test_parse_tddft(self, agent):
        """测试 TDDFT 识别"""
        intent = agent.parse_intent("TDDFT 激发态")
        assert intent.method == "TDDFT"
        assert intent.calc_type == "excited"

    def test_parse_casscf(self, agent):
        """测试 CASSCF 识别"""
        intent = agent.parse_intent("CASSCF(6,6) 计算")
        assert intent.method == "CASSCF"
        assert intent.norb == 6
        assert intent.nelec == 6

    def test_generate_code_hf(self, agent):
        """测试 HF 代码生成"""
        result = agent.process_request("用 RHF 计算水分子的能量")
        assert result["code"] is not None
        assert "scf" in result["script"].lower() or "rhf" in result["script"].lower()
        assert "水" in result["script"] or "H2O" in result["script"] or "h2o" in result["script"].lower()

    def test_generate_code_dft(self, agent):
        """测试 DFT 代码生成"""
        result = agent.process_request("用 B3LYP 计算水分子")
        assert result["code"] is not None
        assert "b3lyp" in result["script"].lower() or "B3LYP" in result["script"]

    def test_generate_code_mp2(self, agent):
        """测试 MP2 代码生成"""
        result = agent.process_request("用 MP2 计算氨分子")
        assert result["code"] is not None
        assert "mp2" in result["script"].lower() or "MP2" in result["script"]

    def test_generate_code_tddft(self, agent):
        """测试 TDDFT 代码生成"""
        result = agent.process_request("计算苯的 TDDFT 激发态")
        assert result["code"] is not None
        assert "tddft" in result["script"].lower() or "TDDFT" in result["script"]

    def test_generate_code_geometry(self, agent):
        """测试几何优化代码生成"""
        result = agent.process_request("优化水分子的几何结构")
        assert result["code"] is not None
        assert "optimize" in result["script"].lower() or "geom" in result["script"].lower()

    def test_confidence_high(self, agent):
        """测试高置信度解析"""
        intent = agent.parse_intent("计算水分子在 B3LYP/6-31G* 水平的能量")
        assert intent.confidence > 0.7

    def test_confidence_low(self, agent):
        """测试低置信度解析（无分子）"""
        intent = agent.parse_intent("计算一下")
        assert intent.confidence < 0.8  # 无分子时置信度应该较低
        assert intent.molecule is None

    def test_warnings_no_molecule(self, agent):
        """测试无分子警告"""
        result = agent.process_request("用 B3LYP 计算能量")
        assert len(result["warnings"]) > 0


class TestParsedIntent:
    """解析意图测试类"""

    def test_defaults(self):
        """测试默认值"""
        intent = ParsedIntent()
        assert intent.molecule is None
        assert intent.method is None
        assert intent.basis is None
        assert intent.calc_type is None
        assert intent.accuracy == "medium"
        assert intent.warnings == []

    def test_confidence_calculation(self):
        """测试置信度计算"""
        agent = FrankAgent()
        intent = agent.parse_intent("计算水分子在 B3LYP/6-31G* 水平的能量")
        assert 0 <= intent.confidence <= 1
