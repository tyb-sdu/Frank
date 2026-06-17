from dataclasses import dataclass


@dataclass
class SCFMethod:
    name: str
    name_cn: str
    pyscf_class: str
    description: str
    when_to_use: str
    restrictions: str


SCF_METHODS: dict[str, SCFMethod] = {}


def _add(m: SCFMethod):
    SCF_METHODS[m.name] = m
    SCF_METHODS[m.name.lower()] = m


_add(SCFMethod(
    name="RHF",
    name_cn="限制性 Hartree-Fock",
    pyscf_class="scf.RHF",
    description="限制性 Hartree-Fock 方法，假设所有电子成对",
    when_to_use="闭壳层分子的基态计算",
    restrictions="仅适用于闭壳层（单重态）分子",
))

_add(SCFMethod(
    name="UHF",
    name_cn="非限制性 Hartree-Fock",
    pyscf_class="scf.UHF",
    description="非限制性 Hartree-Fock 方法，允许 α 和 β 电子不同空间轨道",
    when_to_use="开壳层分子、自由基、双自由基",
    restrictions="可能存在自旋污染",
))

_add(SCFMethod(
    name="ROHF",
    name_cn="限制性开壳层 Hartree-Fock",
    pyscf_class="scf.ROHF",
    description="限制性开壳层 HF，避免自旋污染",
    when_to_use="开壳层分子需要避免自旋污染时",
    restrictions="收敛可能较慢",
))

_add(SCFMethod(
    name="HF",
    name_cn="Hartree-Fock",
    pyscf_class="scf.RHF",
    description="Hartree-Fock 方法（默认使用 RHF）",
    when_to_use="基础计算、参考波函数",
    restrictions="不包含电子相关",
))


def get_scf_method(name: str) -> SCFMethod:
    name_upper = name.upper()
    name_lower = name.lower()
    if name_upper in SCF_METHODS:
        return SCF_METHODS[name_upper]
    if name_lower in SCF_METHODS:
        return SCF_METHODS[name_lower]
    raise KeyError(f"未找到 SCF 方法: {name}")


def choose_scf_type(spin: int) -> str:
    if spin == 0:
        return "RHF"
    else:
        return "UHF"
