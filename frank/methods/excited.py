from dataclasses import dataclass


@dataclass
class ExcitedMethod:
    name: str
    name_cn: str
    pyscf_class: str
    description: str
    when_to_use: str
    cost_scaling: str
    accuracy: str
    n_states_default: int = 6
    notes: str = ""


EXCITED_METHODS: dict[str, ExcitedMethod] = {}


def _add(m: ExcitedMethod):
    EXCITED_METHODS[m.name] = m
    EXCITED_METHODS[m.name.lower()] = m


_add(ExcitedMethod(
    name="TDDFT",
    name_cn="含时密度泛函理论",
    pyscf_class="tdscf.TDDFT",
    description="基于 DFT 基态的含时线性响应理论",
    when_to_use="中大分子的吸收光谱、激发能",
    cost_scaling="O(N^3 ~ N^4)",
    accuracy="medium",
    n_states_default=6,
    notes="最常用的激发态方法，适合有机分子",
))

_add(ExcitedMethod(
    name="TDA",
    name_cn="Tamm-Dancoff 近似",
    pyscf_class="tdscf.TDA",
    description="TDDFT 的 Tamm-Dancoff 近似",
    when_to_use="TDDFT 的简化版本，避免赝对称性问题",
    cost_scaling="O(N^3 ~ N^4)",
    accuracy="medium",
    n_states_default=6,
    notes="比 full TDDFT 更稳定",
))

_add(ExcitedMethod(
    name="CIS",
    name_cn="组态相互作用单激发",
    pyscf_class="ci.CIS",
    description="最简单的激发态方法，仅含单激发",
    when_to_use="初步激发态计算、HF 框架下的激发态",
    cost_scaling="O(N^4)",
    accuracy="low",
    n_states_default=6,
    notes="不包含电子相关，通常不够准确",
))

_add(ExcitedMethod(
    name="ADC(2)",
    name_cn="代数图构造二阶",
    pyscf_class="adc.ADC",
    description="二阶代数图构造方法",
    when_to_use="高精度激发态计算",
    cost_scaling="O(N^5)",
    accuracy="high",
    n_states_default=6,
    notes="比 TDDFT 更准确，但成本更高",
))

_add(ExcitedMethod(
    name="EOM-CCSD",
    name_cn="运动方程 CCSD",
    pyscf_class="cc.EOMCCSD",
    description="基于 CCSD 的 EOM 方法",
    when_to_use="高精度激发态、电离能、电子亲和能",
    cost_scaling="O(N^6)",
    accuracy="very-high",
    n_states_default=3,
    notes="非常昂贵，仅适用于小分子",
))

_add(ExcitedMethod(
    name="STEOM-CCSD",
    name_cn="简化的运动方程 CCSD",
    pyscf_class="cc.EOMCCSD",
    description="简化版本的 EOM-CCSD",
    when_to_use="中等精度激发态计算",
    cost_scaling="O(N^5 ~ N^6)",
    accuracy="high",
    n_states_default=6,
    notes="比 EOM-CCSD 便宜，但精度稍低",
))

_add(ExcitedMethod(
    name="SFCI",
    name_cn="选择性全 CI",
    pyscf_class="fci.FCI",
    description="选择性全组态相互作用",
    when_to_use="小分子精确激发态",
    cost_scaling="指数",
    accuracy="exact",
    n_states_default=3,
    notes="仅适用于非常小的体系",
))


def get_excited_method(name: str) -> ExcitedMethod:
    name_lower = name.lower().strip()
    if name_lower in EXCITED_METHODS:
        return EXCITED_METHODS[name_lower]
    mapping = {
        "td-dft": "TDDFT",
        "td_dft": "TDDFT",
    }
    if name_lower in mapping:
        return EXCITED_METHODS[mapping[name_lower]]
    raise KeyError(f"未找到激发态方法: {name}")


def list_excited_methods() -> list[ExcitedMethod]:
    seen = set()
    result = []
    for m in EXCITED_METHODS.values():
        if m.name not in seen:
            seen.add(m.name)
            result.append(m)
    return sorted(result, key=lambda x: x.name)


def recommend_excited_method(accuracy: str = "medium", n_states: int = 6) -> tuple[str, int]:
    if accuracy == "very-high":
        return "EOM-CCSD", min(n_states, 3)
    elif accuracy == "high":
        return "ADC(2)", n_states
    else:
        return "TDDFT", n_states
