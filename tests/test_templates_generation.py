"""生成代码的语法编译与路由校验测试。

对全部方法/计算类型生成 PySCF 脚本并用 compile() 做语法检查，
确保模板不会产出语法错误的代码；同时校验方法路由与溶剂化模型正确接入。
"""

import pytest

from frank.templates.pyscf_templates import PySCFTemplateEngine


@pytest.fixture
def engine():
    return PySCFTemplateEngine()


def _compile(code) -> str:
    """将 GeneratedCode 编译为字节码以检查语法，返回脚本文本。"""
    script = code.to_script()
    compile(script, "<generated>", "exec")
    return script


# ------------------------------------------------------------
# 覆盖各计算类型 / 方法的语法编译
# ------------------------------------------------------------

ENERGY_METHODS = [
    "HF", "RHF", "B3LYP", "PBE0", "M06-2X", "wB97X-D",
    "MP2", "CCSD", "CCSD(T)", "CISD", "FCI",
]


@pytest.mark.parametrize("method", ENERGY_METHODS)
def test_energy_methods_compile(engine, method):
    code = engine.generate_custom("h2o", method=method, basis="cc-pvdz", calc_type="energy")
    _compile(code)


@pytest.mark.parametrize("calc_type", ["energy", "geometry", "frequency", "nbo"])
def test_calc_types_compile(engine, calc_type):
    code = engine.generate_custom("h2o", method="B3LYP", basis="6-31g*", calc_type=calc_type)
    _compile(code)


@pytest.mark.parametrize("method", ["TDDFT", "ADC(2)", "EOM-CCSD"])
def test_excited_methods_compile(engine, method):
    code = engine.generate_custom("c2h4", method=method, basis="cc-pvdz",
                                  calc_type="excited", n_states=3)
    _compile(code)


@pytest.mark.parametrize("method", ["CASSCF", "CASCI", "NEVPT2", "CASPT2"])
def test_multiref_methods_compile(engine, method):
    code = engine.generate_custom("n2", method=method, basis="cc-pvdz",
                                  calc_type="casscf", norb=6, nelec=6)
    _compile(code)


# ------------------------------------------------------------
# 路由正确性
# ------------------------------------------------------------

def test_nevpt2_routes_to_nevpt2(engine):
    code = engine.generate_custom("h2o", method="NEVPT2", basis="cc-pvdz")
    assert "NEVPT2" in code.title
    assert "mrpt.NEVPT2" in code.to_script()


def test_caspt2_falls_back_to_nevpt2(engine):
    code = engine.generate_custom("h2o", method="CASPT2", basis="cc-pvdz")
    # PySCF 核心无 CASPT2，应等价替换为 NEVPT2
    assert "mrpt.NEVPT2" in code.to_script()
    assert "NEVPT2" in code.description


def test_adc_routes_to_adc(engine):
    code = engine.generate_custom("h2o", method="ADC(2)", basis="cc-pvdz", calc_type="excited")
    assert "adc.ADC" in code.to_script()


def test_eom_ccsd_routes_correctly(engine):
    code = engine.generate_custom("h2o", method="EOM-CCSD", basis="cc-pvdz", calc_type="excited")
    assert "eomee_ccsd_singlet" in code.to_script()


def test_unknown_method_raises_informative_error(engine):
    with pytest.raises(ValueError, match="暂不支持"):
        engine.generate_custom("h2o", method="NOTAMETHOD", basis="cc-pvdz")


# ------------------------------------------------------------
# 溶剂化模型
# ------------------------------------------------------------

def test_smd_model_generates_smd_code(engine):
    code = engine.generate_custom("ch3oh", method="B3LYP", basis="6-31g*",
                                  calc_type="solvation", solvent="water", solvent_model="SMD")
    script = code.to_script()
    assert "smd.SMD" in script
    _compile(code)


@pytest.mark.parametrize("model,pcm_method", [
    ("PCM", "IEF-PCM"),
    ("CPCM", "C-PCM"),
    ("COSMO", "COSMO"),
])
def test_pcm_family_models(engine, model, pcm_method):
    code = engine.generate_custom("ch3oh", method="HF", basis="6-31g*",
                                  calc_type="energy", solvent="ethanol", solvent_model=model)
    script = code.to_script()
    assert pcm_method in script
    _compile(code)


# ------------------------------------------------------------
# agent 解析 -> 生成 端到端（守护关键词与路由的连通）
# ------------------------------------------------------------

@pytest.mark.parametrize("query,expected_method,expected_marker", [
    ("苯的NEVPT2计算", "NEVPT2", "mrpt.NEVPT2"),
    ("水的CASPT2", "CASPT2", "mrpt.NEVPT2"),
    ("乙烯的ADC(2)激发态", "ADC(2)", "adc.ADC"),
    ("氮气的EOM-CCSD激发态", "EOM-CCSD", "eomee_ccsd_singlet"),
    ("水的FCI", "FCI", "fci.FCI"),
    ("水的CISD计算", "CISD", "ci.CISD"),
])
def test_agent_parse_and_generate(query, expected_method, expected_marker):
    from frank.agent import FrankAgent
    agent = FrankAgent()
    intent = agent.parse_intent(query, use_session=False)
    assert intent.method == expected_method
    code = agent.generate_code(intent)
    script = code.to_script()
    assert expected_marker in script
    compile(script, "<generated>", "exec")


@pytest.mark.parametrize("query,expected_solvent,expected_model", [
    ("甲醇在水中的SMD溶剂化", "water", "SMD"),
    ("乙醇在乙腈中用CPCM", "acetonitrile", "CPCM"),
])
def test_agent_solvation_model(query, expected_solvent, expected_model):
    from frank.agent import FrankAgent
    agent = FrankAgent()
    intent = agent.parse_intent(query, use_session=False)
    assert intent.solvent == expected_solvent
    assert intent.solvation_model == expected_model
    code = agent.generate_code(intent)
    compile(code.to_script(), "<generated>", "exec")


def test_ccsd_does_not_shadow_module(engine):
    # 生成的 CCSD 代码不应把 cc 模块名覆盖为对象
    code = engine.generate_custom("h2o", method="CCSD", basis="cc-pvdz")
    script = code.to_script()
    assert "mycc = cc.CCSD" in script
    # 不应有裸的 `cc = cc.CCSD(...)` 覆盖模块名（按行判断，避免匹配到 mycc）
    assert not any(line.strip().startswith("cc = cc.CCSD") for line in script.splitlines())
