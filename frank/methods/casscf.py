from dataclasses import dataclass


@dataclass
class MultiRefMethod:
    name: str
    name_cn: str
    pyscf_class: str
    description: str
    when_to_use: str
    cost_scaling: str
    accuracy: str
    notes: str = ""


MULTIREF_METHODS: dict[str, MultiRefMethod] = {}


def _add(m: MultiRefMethod):
    MULTIREF_METHODS[m.name] = m
    MULTIREF_METHODS[m.name.lower()] = m


_add(MultiRefMethod(
    name="CASSCF",
    name_cn="完全活性空间 SCF",
    pyscf_class="mcscf.CASSCF",
    description="在活性空间内进行 Full-CI，活性空间外进行 SCF",
    when_to_use="键断裂、双自由基、过渡金属、近简并态",
    cost_scaling="指数于活性空间",
    accuracy="high",
    notes="需要选择活性空间 (norb, nelec)",
))

_add(MultiRefMethod(
    name="CASCI",
    name_cn="完全活性空间 CI",
    pyscf_class="mcscf.CASCI",
    description="在给定轨道上进行活性空间 CI",
    when_to_use="CASSCF 的简化版，不优化轨道",
    cost_scaling="指数于活性空间",
    accuracy="medium",
    notes="比 CASSCF 便宜，但不优化轨道",
))

_add(MultiRefMethod(
    name="CASPT2",
    name_cn="二阶 CAS 微扰理论",
    pyscf_class="mcpt.CASPT2",
    description="在 CASSCF 基础上加二阶微扰校正",
    when_to_use="需要动态相关的多参考态计算",
    cost_scaling="O(N^5) × 活性空间",
    accuracy="very-high",
    notes="PySCF 中通过 dmrg-casscf 或外部接口",
))

_add(MultiRefMethod(
    name="NEVPT2",
    name_cn="N-Electron Valence State Perturbation Theory",
    pyscf_class="mrpt.NEVPT2",
    description="无入侵态的多参考微扰理论",
    when_to_use="CASPT2 的替代方案，无入侵态问题",
    cost_scaling="O(N^5) × 活性空间",
    accuracy="very-high",
    notes="比 CASPT2 更稳定",
))

_add(MultiRefMethod(
    name="DMRG-CASSCF",
    name_cn="DMRG-CASSCF",
    pyscf_class="dmrgscf.DMRGSCF",
    description="使用 DMRG 求解器的 CASSCF，可处理更大活性空间",
    when_to_use="大活性空间 (>16 轨道)",
    cost_scaling="多项式于活性空间",
    accuracy="high",
    notes="需要 Block 或 CheMPS2 接口",
))

_add(MultiRefMethod(
    name="XMS-CASPT2",
    name_cn="Extended Multi-State CASPT2",
    pyscf_class="mcpt.CASPT2",
    description="扩展多态 CASPT2",
    when_to_use="多个电子态之间的耦合",
    cost_scaling="O(N^5) × 活性空间",
    accuracy="very-high",
    notes="处理态交叉问题",
))

_add(MultiRefMethod(
    name="MRCI",
    name_cn="多参考态组态相互作用",
    pyscf_class="ci.MRCI",
    description="在 CASSCF 参考态上进行 CI 展开",
    when_to_use="高精度多参考态计算",
    cost_scaling="O(N^6) × 活性空间",
    accuracy="very-high",
    notes="非常昂贵，仅适用于小体系",
))


def get_multiref_method(name: str) -> MultiRefMethod:
    name_upper = name.upper()
    name_lower = name.lower()
    if name_upper in MULTIREF_METHODS:
        return MULTIREF_METHODS[name_upper]
    if name_lower in MULTIREF_METHODS:
        return MULTIREF_METHODS[name_lower]
    raise KeyError(f"未找到多参考态方法: {name}")


def list_multiref_methods() -> list[MultiRefMethod]:
    seen = set()
    result = []
    for m in MULTIREF_METHODS.values():
        if m.name not in seen:
            seen.add(m.name)
            result.append(m)
    return sorted(result, key=lambda x: x.name)


def recommend_casscf_space(mol_electrons: int, mol_name: str = "") -> tuple[int, int]:
    common_spaces = {
        "h2o": (4, 4),
        "n2": (6, 6),
        "o2": (6, 8),
        "co": (6, 6),
        "no": (6, 7),
        "c2h4": (4, 4),
        "c2h2": (4, 4),
        "benzene": (6, 6),
        "c6h6": (6, 6),
    }
    mol_name_lower = mol_name.lower()
    if mol_name_lower in common_spaces:
        return common_spaces[mol_name_lower]
    n_occ = mol_electrons // 2
    n_virt = max(2, mol_electrons // 4)
    norb = min(n_occ + n_virt, 10)
    nelec = mol_electrons
    return (norb, nelec)
