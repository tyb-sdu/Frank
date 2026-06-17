from dataclasses import dataclass, field


@dataclass
class RelativisticMethod:
    name: str
    name_cn: str
    pyscf_keyword: str
    description: str
    when_to_use: str
    accuracy: str
    notes: str = ""
    order: int = 1


RELATIVISTIC_METHODS: dict[str, RelativisticMethod] = {}


def _add(m: RelativisticMethod):
    RELATIVISTIC_METHODS[m.name] = m
    RELATIVISTIC_METHODS[m.name.lower()] = m


_add(RelativisticMethod(
    name="DKH0",
    name_cn="零阶 Douglas-Kroll-Hess",
    pyscf_keyword="DKH0",
    description="零阶 DKH，仅包含质量-速度和 Darwin 项",
    when_to_use="快速相对论校正",
    accuracy="low",
    order=0,
))

_add(RelativisticMethod(
    name="DKH1",
    name_cn="一阶 Douglas-Kroll-Hess",
    pyscf_keyword="DKH",
    description="一阶 DKH，包含主要的标量相对论效应",
    when_to_use="一般相对论计算",
    accuracy="medium",
    order=1,
))

_add(RelativisticMethod(
    name="DKH2",
    name_cn="二阶 Douglas-Kroll-Hess",
    pyscf_keyword="DKH",
    description="二阶 DKH，更高的相对论精度",
    when_to_use="需要高精度相对论效应时",
    accuracy="high",
    order=2,
))

_add(RelativisticMethod(
    name="X2C",
    name_cn="精确二分量方法",
    pyscf_keyword="X2C",
    description="精确二分量方法，等价于四分量的标量部分",
    when_to_use="最高精度的标量相对论计算",
    accuracy="very-high",
    notes="比 DKH 更精确，但计算量稍大",
))

_add(RelativisticMethod(
    name="SF-X2C",
    name_cn="自旋自由度 X2C",
    pyscf_keyword="SF-X2C",
    description="包含自旋-轨道耦合的 X2C",
    when_to_use="需要自旋-轨道耦合效应时",
    accuracy="very-high",
    notes="包含自旋-轨道耦合",
))

_add(RelativisticMethod(
    name="ECP",
    name_cn="有效核势",
    pyscf_keyword="ECP",
    description="使用赝势替代内层电子，隐式包含相对论效应",
    when_to_use="重元素（过渡金属、镧系、锕系）",
    accuracy="medium",
    notes="需要配合 ECP 基组使用，如 LANL2DZ, def2-SVP",
))


def get_relativistic_method(name: str) -> RelativisticMethod:
    name_upper = name.upper()
    name_lower = name.lower()
    if name_upper in RELATIVISTIC_METHODS:
        return RELATIVISTIC_METHODS[name_upper]
    if name_lower in RELATIVISTIC_METHODS:
        return RELATIVISTIC_METHODS[name_lower]
    mapping = {
        "dkh": "DKH2",
        "douglas-kroll": "DKH2",
        "relativistic": "DKH2",
    }
    if name_lower in mapping:
        return RELATIVISTIC_METHODS[mapping[name_lower]]
    raise KeyError(f"未找到相对论方法: {name}")


def list_relativistic_methods() -> list[RelativisticMethod]:
    seen = set()
    result = []
    for m in RELATIVISTIC_METHODS.values():
        if m.name not in seen:
            seen.add(m.name)
            result.append(m)
    return sorted(result, key=lambda x: x.order)


def recommend_relativistic_method(elements: list[str]) -> str:
    heavy_elements = {
        "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
        "In", "Sn", "Sb", "Te", "I", "Xe",
        "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb",
        "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
        "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
        "Tl", "Pb", "Bi", "Po", "At", "Rn",
    }
    very_heavy_elements = {
        "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm",
        "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr",
    }
    has_heavy = any(e in heavy_elements for e in elements)
    has_very_heavy = any(e in very_heavy_elements for e in elements)
    if has_very_heavy:
        return "X2C"
    elif has_heavy:
        return "DKH2"
    else:
        return "None"


def get_ecp_for_element(element: str) -> str:
    transition_metals = {
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
        "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
        "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    }
    lanthanides = {"La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd",
                   "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu"}
    actinides = {"Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm",
                 "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr"}
    if element in transition_metals:
        return "lanl2dz"
    elif element in lanthanides or element in actinides:
        return "lanl2dz"
    else:
        return "def2-svp"
