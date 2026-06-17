from dataclasses import dataclass, field


@dataclass
class DFTFunctional:
    name: str
    name_cn: str
    category: str
    description: str
    when_to_use: str
    accuracy: str
    has_dispersion: bool = False
    notes: str = ""
    aliases: list[str] = field(default_factory=list)


DFT_FUNCTIONALS: dict[str, DFTFunctional] = {}


def _add(f: DFTFunctional):
    DFT_FUNCTIONALS[f.name.lower()] = f
    for alias in f.aliases:
        DFT_FUNCTIONALS[alias.lower()] = f


_add(DFTFunctional(
    name="LDA",
    name_cn="局域密度近似",
    category="LDA",
    description="最简单的 DFT 泛函，仅依赖电子密度",
    when_to_use="基准测试、教学",
    accuracy="low",
    notes="通常不够准确，但计算速度快",
    aliases=["svwn", "vwn"],
))

_add(DFTFunctional(
    name="LDA,VWN",
    name_cn="VWN LDA",
    category="LDA",
    description="Vosko-Wilk-Nusair LDA 参数化",
    when_to_use="LDA 计算的标准选择",
    accuracy="low",
    aliases=[],
))

_add(DFTFunctional(
    name="PBE",
    name_cn="Perdew-Burke-Ernzerhof",
    category="GGA",
    description="最流行的 GGA 泛函之一",
    when_to_use="固体物理、周期性体系、通用计算",
    accuracy="medium",
    notes="无经验参数，物理基础良好",
    aliases=["pbe"],
))

_add(DFTFunctional(
    name="BLYP",
    name_cn="Becke-Lee-Yang-Parr",
    category="GGA",
    description="Becke 交换 + LYP 相关",
    when_to_use="通用 GGA 计算",
    accuracy="medium",
    aliases=["blyp"],
))

_add(DFTFunctional(
    name="BP86",
    name_cn="Becke-Perdew 86",
    category="GGA",
    description="Becke 交换 + P86 相关",
    when_to_use="过渡金属配合物",
    accuracy="medium",
    aliases=["bp86"],
))

_add(DFTFunctional(
    name="PW91",
    name_cn="Perdew-Wang 91",
    category="GGA",
    description="Perdew-Wang 1991 年泛函",
    when_to_use="固体物理",
    accuracy="medium",
    aliases=["pw91"],
))

_add(DFTFunctional(
    name="B97",
    name_cn="Becke 97",
    category="GGA",
    description="Becke 97 泛函系列",
    when_to_use="通用计算",
    accuracy="medium",
    aliases=["b97"],
))

_add(DFTFunctional(
    name="OLYP",
    name_cn="OPTX-LYP",
    category="GGA",
    description="OPTX 交换 + LYP 相关",
    when_to_use="反应能垒计算",
    accuracy="medium",
    aliases=["olyp"],
))

_add(DFTFunctional(
    name="RPBE",
    name_cn="revised PBE",
    category="GGA",
    description="PBE 的修订版",
    when_to_use="表面化学、吸附",
    accuracy="medium",
    aliases=["rpbe"],
))

_add(DFTFunctional(
    name="revPBE",
    name_cn="revised PBE",
    category="GGA",
    description="PBE 的另一个修订版",
    when_to_use="表面化学",
    accuracy="medium",
    aliases=["revpbe"],
))

_add(DFTFunctional(
    name="TPSS",
    name_cn="Tao-Perdew-Staroverov-Scuseria",
    category="meta-GGA",
    description="无经验参数的 meta-GGA 泛函",
    when_to_use="需要比 GGA 更高精度时",
    accuracy="medium",
    aliases=["tpss"],
))

_add(DFTFunctional(
    name="M06-L",
    name_cn="Minnesota 06-L",
    category="meta-GGA",
    description="Minnesota 系列的局域 meta-GGA 泛函",
    when_to_use="过渡金属、有机金属",
    accuracy="medium",
    has_dispersion=True,
    aliases=["m06l", "m06-l"],
))

_add(DFTFunctional(
    name="SCAN",
    name_cn="Strongly Constrained and Appropriately Normed",
    category="meta-GGA",
    description="满足所有已知精确约束的 meta-GGA",
    when_to_use="高精度固体和分子计算",
    accuracy="high",
    aliases=["scan"],
))

_add(DFTFunctional(
    name="r2SCAN",
    name_cn="regularized SCAN",
    category="meta-GGA",
    description="SCAN 的正则化版本，数值更稳定",
    when_to_use="SCAN 的替代，数值稳定性更好",
    accuracy="high",
    aliases=["r2scan"],
))

_add(DFTFunctional(
    name="B3LYP",
    name_cn="Becke 3-parameter Lee-Yang-Parr",
    category="hybrid",
    description="最广泛使用的杂化泛函（20% HF 交换）",
    when_to_use="有机分子、通用计算、最常用泛函",
    accuracy="medium",
    notes="经典泛函，但对非共价相互作用描述不佳",
    aliases=["b3lyp"],
))

_add(DFTFunctional(
    name="PBE0",
    name_cn="PBE Hybrid",
    category="hybrid",
    description="PBE 杂化泛函（25% HF 交换）",
    when_to_use="通用杂化泛函，对固体也适用",
    accuracy="medium",
    aliases=["pbe0"],
))

_add(DFTFunctional(
    name="B3LYP-D3(BJ)",
    name_cn="B3LYP + D3(BJ) 色散校正",
    category="hybrid",
    description="B3LYP 加 Becke-Johnson 阻尼的 D3 色散校正",
    when_to_use="非共价相互作用、构象分析",
    accuracy="medium",
    has_dispersion=True,
    aliases=["b3lyp-d3bj", "b3lyp-d3"],
))

_add(DFTFunctional(
    name="PBE0-D3(BJ)",
    name_cn="PBE0 + D3(BJ) 色散校正",
    category="hybrid",
    description="PBE0 加 D3(BJ) 色散校正",
    when_to_use="非共价相互作用",
    accuracy="medium",
    has_dispersion=True,
    aliases=["pbe0-d3bj", "pbe0-d3"],
))

_add(DFTFunctional(
    name="M06-2X",
    name_cn="Minnesota 06-2X",
    category="hybrid",
    description="Minnesota 系列杂化泛函（54% HF 交换）",
    when_to_use="热化学、动力学、非共价相互作用",
    accuracy="high",
    has_dispersion=True,
    notes="对热化学和动力学特别好",
    aliases=["m062x", "m06-2x"],
))

_add(DFTFunctional(
    name="M06",
    name_cn="Minnesota 06",
    category="hybrid",
    description="Minnesota 06 杂化泛函",
    when_to_use="通用计算、过渡金属",
    accuracy="medium",
    has_dispersion=True,
    aliases=["m06"],
))

_add(DFTFunctional(
    name="M06-HF",
    name_cn="Minnesota 06-HF",
    category="hybrid",
    description="100% HF 交换的 Minnesota 泛函",
    when_to_use="长程电荷转移、激发态",
    accuracy="medium",
    has_dispersion=True,
    aliases=["m06hf", "m06-hf"],
))

_add(DFTFunctional(
    name="TPSSh",
    name_cn="TPSS Hybrid",
    category="hybrid",
    description="TPSS 杂化泛函（10% HF 交换）",
    when_to_use="过渡金属、需要 meta-GGA 精度时",
    accuracy="medium",
    aliases=["tpssh"],
))

_add(DFTFunctional(
    name="B97-1",
    name_cn="Becke 97-1",
    category="hybrid",
    description="Becke 97 系列的杂化泛函",
    when_to_use="通用杂化泛函",
    accuracy="medium",
    aliases=["b971"],
))

_add(DFTFunctional(
    name="X3LYP",
    name_cn="Extended B3LYP",
    category="hybrid",
    description="扩展的 B3LYP 泛函",
    when_to_use="非共价相互作用、氢键",
    accuracy="medium",
    aliases=["x3lyp"],
))

_add(DFTFunctional(
    name="O3LYP",
    name_cn="OPTX-B3LYP",
    category="hybrid",
    description="使用 OPTX 交换的 B3LYP 变体",
    when_to_use="通用杂化泛函",
    accuracy="medium",
    aliases=["o3lyp"],
))

_add(DFTFunctional(
    name="HSE06",
    name_cn="Heyd-Scuseria-Ernzerhof 06",
    category="range-separated",
    description="短程杂化泛函（固体计算首选）",
    when_to_use="固体能带结构、带隙计算",
    accuracy="high",
    notes="短程 PBE0，长程 PBE",
    aliases=["hse06", "hse"],
))

_add(DFTFunctional(
    name="CAM-B3LYP",
    name_cn="Coulomb-Attenuating B3LYP",
    category="range-separated",
    description="范围分离的 B3LYP",
    when_to_use="电荷转移激发态、Rydberg 态",
    accuracy="high",
    aliases=["cam-b3lyp"],
))

_add(DFTFunctional(
    name="ωB97X-D",
    name_cn="Chai-Head-Gordon ωB97X-D",
    category="range-separated",
    description="范围分离杂化泛函 + 色散校正",
    when_to_use="非共价相互作用、激发态、通用高精度",
    accuracy="high",
    has_dispersion=True,
    notes="非常全面的泛函",
    aliases=["wb97x-d", "wb97xd"],
))

_add(DFTFunctional(
    name="ωB97X-V",
    name_cn="ωB97X with VV10 correlation",
    category="range-separated",
    description="范围分离杂化泛函 + VV10 非局域相关",
    when_to_use="高精度通用计算",
    accuracy="high",
    has_dispersion=True,
    aliases=["wb97x-v", "wb97xv"],
))

_add(DFTFunctional(
    name="ωB97M-V",
    name_cn="ωB97M with VV10 correlation",
    category="range-separated",
    description="范围分离 meta-杂化泛函 + VV10",
    when_to_use="最高精度 DFT 计算",
    accuracy="high",
    has_dispersion=True,
    aliases=["wb97m-v", "wb97mv"],
))

_add(DFTFunctional(
    name="LC-BLYP",
    name_cn="Long-range Corrected BLYP",
    category="range-separated",
    description="长程校正的 BLYP",
    when_to_use="长程电荷转移",
    accuracy="medium",
    aliases=["lc-blyp"],
))

_add(DFTFunctional(
    name="LC-ωPBE",
    name_cn="Long-range Corrected ωPBE",
    category="range-separated",
    description="长程校正的 PBE",
    when_to_use="长程电荷转移、Rydberg 态",
    accuracy="medium",
    aliases=["lc-wpbe", "lcwpbe"],
))

_add(DFTFunctional(
    name="B2PLYP",
    name_cn="Becke 2-parameter Double Hybrid",
    category="double-hybrid",
    description="双杂化泛函（53% HF 交换 + 27% MP2 相关）",
    when_to_use="高精度热化学、反应能",
    accuracy="high",
    notes="需要 MP2 计算，成本较高",
    aliases=["b2plyp"],
))

_add(DFTFunctional(
    name="B2PLYP-D3(BJ)",
    name_cn="B2PLYP + D3(BJ) 色散校正",
    category="double-hybrid",
    description="B2PLYP 加 D3(BJ) 色散校正",
    when_to_use="高精度非共价相互作用",
    accuracy="high",
    has_dispersion=True,
    aliases=["b2plyp-d3bj", "b2plyp-d3"],
))

_add(DFTFunctional(
    name="DSD-PBEP86",
    name_cn="Dispersion-corrected Spin-component-scaled Double Hybrid",
    category="double-hybrid",
    description="自旋分量标度双杂化泛函",
    when_to_use="最高精度 DFT 计算",
    accuracy="high",
    has_dispersion=True,
    aliases=["dsd-pbep86", "dsdpbep86"],
))

_add(DFTFunctional(
    name="PWPB95",
    name_cn="PWPB95 Double Hybrid",
    category="double-hybrid",
    description="双杂化 meta-GGA 泛函",
    when_to_use="高精度热化学",
    accuracy="high",
    aliases=["pwpb95"],
))

_add(DFTFunctional(
    name="revDSD-PBEP86-D4",
    name_cn="revised DSD-PBEP86 with D4",
    category="double-hybrid",
    description="修订版 DSD 泛函 + D4 色散校正",
    when_to_use="最高精度通用计算",
    accuracy="high",
    has_dispersion=True,
    aliases=["revdsd-pbep86-d4"],
))


def get_dft_functional(name: str) -> DFTFunctional:
    name_lower = name.lower().strip()
    if name_lower in DFT_FUNCTIONALS:
        return DFT_FUNCTIONALS[name_lower]
    raise KeyError(f"未找到 DFT 泛函: {name}")


def list_dft_functionals(category: str = None) -> list[DFTFunctional]:
    seen = set()
    result = []
    for f in DFT_FUNCTIONALS.values():
        if f.name not in seen:
            seen.add(f.name)
            if category is None or f.category == category:
                result.append(f)
    return sorted(result, key=lambda x: x.name)


def list_dft_categories() -> list[str]:
    return sorted(set(f.category for f in DFT_FUNCTIONALS.values()))


def recommend_dft_functional(
    purpose: str = "general",
    accuracy: str = "medium",
    has_dispersion: bool = False,
) -> str:
    if purpose == "solid" or purpose == "band-gap":
        return "HSE06"
    if purpose == "charge-transfer":
        return "CAM-B3LYP"
    if purpose == "excited":
        if accuracy == "high":
            return "ωB97X-D"
        return "CAM-B3LYP"
    if purpose == "transition-metal":
        if has_dispersion:
            return "M06"
        return "TPSSh"
    if purpose == "non-covalent":
        if accuracy == "high":
            return "ωB97X-D"
        return "B3LYP-D3(BJ)"
    if purpose == "thermo":
        if accuracy == "high":
            return "B2PLYP-D3(BJ)"
        return "M06-2X"
    if accuracy == "high":
        return "ωB97X-D"
    elif accuracy == "medium":
        if has_dispersion:
            return "B3LYP-D3(BJ)"
        return "B3LYP"
    else:
        return "PBE"


def get_xc_string(name: str) -> str:
    special = {
        "wb97x-d": "wb97x-d",
        "wb97x-v": "wb97x-v",
        "wb97m-v": "wb97m-v",
        "cam-b3lyp": "cam-b3lyp",
        "hse06": "hse06",
        "lc-blyp": "lc-blyp",
        "lc-wpbe": "lc-wpbe",
    }
    name_lower = name.lower().strip()
    if name_lower in special:
        return special[name_lower]
    return name_lower
