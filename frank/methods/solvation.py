from dataclasses import dataclass


@dataclass
class Solvent:
    name: str
    name_cn: str
    pyscf_name: str
    dielectric: float
    category: str
    notes: str = ""


@dataclass
class SolvationModel:
    name: str
    name_cn: str
    pyscf_method: str
    description: str
    when_to_use: str
    accuracy: str
    notes: str = ""


SOLVATION_MODELS: dict[str, SolvationModel] = {}


def _add_model(m: SolvationModel):
    SOLVATION_MODELS[m.name] = m
    SOLVATION_MODELS[m.name.lower()] = m


_add_model(SolvationModel(
    name="PCM",
    name_cn="极化连续介质模型",
    pyscf_method="PCM",
    description="将溶剂视为连续极化介质",
    when_to_use="溶剂化能、溶剂中的分子构型",
    accuracy="medium",
    notes="最常用的隐式溶剂模型",
))

_add_model(SolvationModel(
    name="CPCM",
    name_cn="导体极化连续介质模型",
    pyscf_method="CPCM",
    description="PCM 的导体变体",
    when_to_use="PCM 的简化版本",
    accuracy="medium",
    notes="计算更稳定",
))

_add_model(SolvationModel(
    name="SMD",
    name_cn="溶剂化模型密度",
    pyscf_method="SMD",
    description="基于溶剂化模型密度的隐式溶剂",
    when_to_use="精确的溶剂化自由能",
    accuracy="high",
    notes="Marenich-Cramer-Truhlar 模型，精度最好",
))

_add_model(SolvationModel(
    name="COSMO",
    name_cn="导体屏蔽模型",
    pyscf_method="COSMO",
    description="导体屏蔽连续介质模型",
    when_to_use="快速溶剂化计算",
    accuracy="medium",
    notes="比 PCM 更快，适合大体系",
))


SOLVENTS: dict[str, Solvent] = {}


def _add_solvent(s: Solvent):
    SOLVENTS[s.name] = s
    SOLVENTS[s.name.lower()] = s


_add_solvent(Solvent(
    name="water", name_cn="水", pyscf_name="water",
    dielectric=78.355, category="polar-protic",
))

_add_solvent(Solvent(
    name="methanol", name_cn="甲醇", pyscf_name="methanol",
    dielectric=32.613, category="polar-protic",
))

_add_solvent(Solvent(
    name="ethanol", name_cn="乙醇", pyscf_name="ethanol",
    dielectric=24.852, category="polar-protic",
))

_add_solvent(Solvent(
    name="acetone", name_cn="丙酮", pyscf_name="acetone",
    dielectric=20.493, category="polar-aprotic",
))

_add_solvent(Solvent(
    name="dmso", name_cn="二甲亚砜", pyscf_name="dmso",
    dielectric=46.826, category="polar-aprotic",
))

_add_solvent(Solvent(
    name="dichloromethane", name_cn="二氯甲烷", pyscf_name="dichloromethane",
    dielectric=8.93, category="polar-aprotic",
))

_add_solvent(Solvent(
    name="chloroform", name_cn="氯仿", pyscf_name="chloroform",
    dielectric=4.7113, category="polar-aprotic",
))

_add_solvent(Solvent(
    name="toluene", name_cn="甲苯", pyscf_name="toluene",
    dielectric=2.374, category="nonpolar",
))

_add_solvent(Solvent(
    name="benzene", name_cn="苯", pyscf_name="benzene",
    dielectric=2.2706, category="nonpolar",
))

_add_solvent(Solvent(
    name="cyclohexane", name_cn="环己烷", pyscf_name="cyclohexane",
    dielectric=2.016, category="nonpolar",
))

_add_solvent(Solvent(
    name="hexane", name_cn="正己烷", pyscf_name="hexane",
    dielectric=1.88, category="nonpolar",
))

_add_solvent(Solvent(
    name="thf", name_cn="四氢呋喃", pyscf_name="thf",
    dielectric=7.4257, category="polar-aprotic",
))

_add_solvent(Solvent(
    name="acetonitrile", name_cn="乙腈", pyscf_name="acetonitrile",
    dielectric=35.688, category="polar-aprotic",
))

_add_solvent(Solvent(
    name="dioxane", name_cn="二氧六环", pyscf_name="dioxane",
    dielectric=2.2099, category="nonpolar",
))

_add_solvent(Solvent(
    name="nitromethane", name_cn="硝基甲烷", pyscf_name="nitromethane",
    dielectric=36.562, category="polar-aprotic",
))

_add_solvent(Solvent(
    name="heptane", name_cn="正庚烷", pyscf_name="heptane",
    dielectric=1.9113, category="nonpolar",
))

_add_solvent(Solvent(
    name="aniline", name_cn="苯胺", pyscf_name="aniline",
    dielectric=6.8878, category="polar-protic",
))

_add_solvent(Solvent(
    name="chcl3", name_cn="氯仿", pyscf_name="chloroform",
    dielectric=4.7113, category="polar-aprotic",
))

_add_solvent(Solvent(
    name="dcm", name_cn="二氯甲烷", pyscf_name="dichloromethane",
    dielectric=8.93, category="polar-aprotic",
))


def get_solvation_model(name: str) -> SolvationModel:
    name_upper = name.upper()
    name_lower = name.lower()
    if name_upper in SOLVATION_MODELS:
        return SOLVATION_MODELS[name_upper]
    if name_lower in SOLVATION_MODELS:
        return SOLVATION_MODELS[name_lower]
    raise KeyError(f"未找到溶剂化模型: {name}")


def get_solvent(name: str) -> Solvent:
    name_lower = name.lower().strip()
    if name_lower in SOLVENTS:
        return SOLVENTS[name_lower]
    raise KeyError(f"未找到溶剂: {name}")


def list_solvents(category: str = None) -> list[Solvent]:
    if category:
        return [s for s in SOLVENTS.values() if s.category == category]
    return list(SOLVENTS.values())


def list_solvation_models() -> list[SolvationModel]:
    return list(SOLVATION_MODELS.values())


def recommend_solvent(purpose: str = "general") -> str:
    recommendations = {
        "general": "water",
        "organic-synthesis": "dichloromethane",
        "electrochemistry": "acetonitrile",
        "biochemistry": "water",
        "nonpolar": "cyclohexane",
    }
    return recommendations.get(purpose, "water")
