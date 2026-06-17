from dataclasses import dataclass
from typing import Optional


@dataclass
class BasisSet:
    name: str
    description: str
    level: int
    category: str
    notes: str = ""
    for_elements: Optional[list[str]] = None


BASIS_SETS: dict[str, BasisSet] = {}


def _add(bs: BasisSet):
    BASIS_SETS[bs.name] = bs


_add(BasisSet(
    name="sto-3g",
    description="最小基组，3个高斯函数拟合1个斯莱特轨道",
    level=1,
    category="minimal",
    notes="仅用于初步测试和教学，不适合正式计算",
))

_add(BasisSet(
    name="sto-6g",
    description="最小基组，6个高斯函数拟合",
    level=1,
    category="minimal",
    notes="比 STO-3G 稍好，但仍不适合正式计算",
))

_add(BasisSet(
    name="3-21g",
    description="劈裂价层基组（2重劈裂）",
    level=2,
    category="split-valence",
    notes="适合几何优化初猜，不适合能量计算",
))

_add(BasisSet(
    name="6-31g",
    description="劈裂价层基组（2重劈裂）",
    level=2,
    category="split-valence",
    notes="基础劈裂价层，适合初步优化",
))

_add(BasisSet(
    name="6-31g*",
    description="劈裂价层 + d 极化函数（重原子）",
    level=3,
    category="split-valence",
    notes="最常用的基组之一，适合几何优化和频率计算",
))

_add(BasisSet(
    name="6-31g(d)",
    description="劈裂价层 + d 极化函数（重原子）",
    level=3,
    category="split-valence",
    notes="等同于 6-31G*",
))

_add(BasisSet(
    name="6-31g**",
    description="劈裂价层 + d 极化函数（重原子）+ p 极化函数（H）",
    level=3,
    category="split-valence",
    notes="对含氢体系更准确",
))

_add(BasisSet(
    name="6-31g(d,p)",
    description="劈裂价层 + d 极化函数（重原子）+ p 极化函数（H）",
    level=3,
    category="split-valence",
    notes="等同于 6-31G**",
))

_add(BasisSet(
    name="6-311g",
    description="劈裂价层基组（3重劈裂）",
    level=3,
    category="split-valence",
    notes="3重劈裂，比 6-31G 更灵活",
))

_add(BasisSet(
    name="6-311g*",
    description="劈裂价层（3重劈裂）+ d 极化函数",
    level=3,
    category="split-valence",
    notes="常用基组",
))

_add(BasisSet(
    name="6-311g(d,p)",
    description="劈裂价层（3重劈裂）+ d,p 极化函数",
    level=4,
    category="split-valence",
    notes="较好的精度/成本平衡",
))

_add(BasisSet(
    name="6-311g(2d,2p)",
    description="劈裂价层 + 2组极化函数",
    level=4,
    category="split-valence",
    notes="更高精度的极化基组",
))

_add(BasisSet(
    name="6-31+g*",
    description="劈裂价层 + 弥散函数 + d 极化函数",
    level=3,
    category="diffuse",
    notes="适合阴离子、激发态、弱相互作用",
))

_add(BasisSet(
    name="6-31+g(d,p)",
    description="劈裂价层 + 弥散函数 + d,p 极化函数",
    level=4,
    category="diffuse",
    notes="适合阴离子和氢键体系",
))

_add(BasisSet(
    name="6-31++g**",
    description="劈裂价层 + 双弥散函数 + 双极化函数",
    level=4,
    category="diffuse",
    notes="适合阴离子、激发态、弱相互作用",
))

_add(BasisSet(
    name="6-31++g(d,p)",
    description="劈裂价层 + 双弥散函数 + d,p 极化函数",
    level=4,
    category="diffuse",
    notes="等同于 6-31++G**",
))

_add(BasisSet(
    name="6-311+g(d,p)",
    description="3重劈裂 + 弥散函数 + d,p 极化函数",
    level=4,
    category="diffuse",
    notes="高精度弥散基组",
))

_add(BasisSet(
    name="cc-pvdz",
    description="Dunning 相关一致双ζ基组",
    level=3,
    category="correlation-consistent",
    notes="相关计算的基础基组",
))

_add(BasisSet(
    name="cc-pvtz",
    description="Dunning 相关一致三ζ基组",
    level=4,
    category="correlation-consistent",
    notes="中等精度相关计算",
))

_add(BasisSet(
    name="cc-pvqz",
    description="Dunning 相关一致四ζ基组",
    level=5,
    category="correlation-consistent",
    notes="高精度相关计算",
))

_add(BasisSet(
    name="cc-pv5z",
    description="Dunning 相关一致五ζ基组",
    level=5,
    category="correlation-consistent",
    notes="接近 CBS 极限",
))

_add(BasisSet(
    name="aug-cc-pvdz",
    description="Dunning 相关一致双ζ + 弥散函数",
    level=4,
    category="augmented",
    notes="适合阴离子、激发态、极化率",
))

_add(BasisSet(
    name="aug-cc-pvtz",
    description="Dunning 相关一致三ζ + 弥散函数",
    level=5,
    category="augmented",
    notes="高精度阴离子和激发态计算",
))

_add(BasisSet(
    name="aug-cc-pvqz",
    description="Dunning 相关一致四ζ + 弥散函数",
    level=5,
    category="augmented",
    notes="接近 CBS 极限的弥散基组",
))

_add(BasisSet(
    name="cc-pwcvdz",
    description="Dunning 相关一致双ζ + 核价函数",
    level=4,
    category="core-valence",
    notes="适合需要考虑内层电子相关的情况",
))

_add(BasisSet(
    name="cc-pwcvtz",
    description="Dunning 相关一致三ζ + 核价函数",
    level=5,
    category="core-valence",
    notes="高精度核价相关计算",
))

_add(BasisSet(
    name="def2-svp",
    description="Ahlrichs 劈裂价层基组",
    level=3,
    category="def2",
    notes="适合过渡金属和重元素",
))

_add(BasisSet(
    name="def2-svpd",
    description="Ahlrichs 劈裂价层 + 弥散函数",
    level=3,
    category="def2",
    notes="适合阴离子和弱相互作用",
))

_add(BasisSet(
    name="def2-tzvp",
    description="Ahlrichs 三ζ价层基组",
    level=4,
    category="def2",
    notes="常用的高精度基组，对过渡金属友好",
))

_add(BasisSet(
    name="def2-tzvpd",
    description="Ahlrichs 三ζ价层 + 弥散函数",
    level=4,
    category="def2",
    notes="适合阴离子和弱相互作用",
))

_add(BasisSet(
    name="def2-qzvp",
    description="Ahlrichs 四ζ价层基组",
    level=5,
    category="def2",
    notes="接近极限的精度",
))

_add(BasisSet(
    name="lanl2dz",
    description="LANL2DZ 赝势基组",
    level=3,
    category="ecp",
    notes="适合过渡金属和重元素（使用赝势）",
    for_elements=["Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
                  "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
                  "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
                  "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn"],
))


def get_basis_set(name: str) -> BasisSet:
    name_lower = name.lower()
    if name_lower in BASIS_SETS:
        return BASIS_SETS[name_lower]
    variants = {
        "6-31g*": "6-31g*",
        "6-31g(d)": "6-31g(d)",
        "6-31g**": "6-31g**",
        "6-31g(d,p)": "6-31g(d,p)",
        "cc-pvdz": "cc-pvdz",
        "cc-pvtz": "cc-pvtz",
    }
    for variant_name, bs_name in variants.items():
        if name_lower == variant_name:
            return BASIS_SETS[bs_name]
    raise KeyError(f"未找到基组: {name}")


def list_basis_sets(category: Optional[str] = None) -> list[BasisSet]:
    if category:
        return [bs for bs in BASIS_SETS.values() if bs.category == category]
    return list(BASIS_SETS.values())


def recommend_basis_set(
    method: str,
    purpose: str = "energy",
    accuracy: str = "medium",
    has_diffuse: bool = False,
) -> str:
    method_lower = method.lower()

    post_hf_methods = ["mp2", "mp3", "mp4", "ccsd", "ccsd(t)", "casscf", "caspt2", "nevpt2"]
    is_post_hf = any(m in method_lower for m in post_hf_methods)

    excited_methods = ["tddft", "td-dft", "eom-ccsd", "cis", "caspt2"]
    is_excited = any(m in method_lower for m in excited_methods)

    if is_post_hf:
        if accuracy == "high":
            base = "aug-cc-pvtz" if has_diffuse else "cc-pvtz"
        elif accuracy == "medium":
            base = "aug-cc-pvdz" if has_diffuse else "cc-pvdz"
        else:
            base = "cc-pvdz"
    elif is_excited:
        if accuracy == "high":
            base = "aug-cc-pvtz"
        elif accuracy == "medium":
            base = "aug-cc-pvdz"
        else:
            base = "6-31+g*"
    else:
        if accuracy == "high":
            base = "aug-cc-pvtz" if has_diffuse else "cc-pvtz"
        elif accuracy == "medium":
            base = "6-31+g*" if has_diffuse else "6-31g*"
        else:
            base = "6-31g*"

    return base


def get_basis_set_for_element(basis_name: str, element: str) -> bool:
    bs = get_basis_set(basis_name)
    if bs.for_elements is None:
        return True
    return element in bs.for_elements
