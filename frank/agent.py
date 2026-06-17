import re
from dataclasses import dataclass, field
from typing import Optional

from .molecules.database import get_molecule, list_molecules, search_molecules, Molecule
from .molecules.sources import resolve_molecule, register_molecule
from .basis import recommend_basis_set, get_basis_set, list_basis_sets
from .methods.dft import get_dft_functional, list_dft_functionals, recommend_dft_functional
from .methods.post_hf import get_post_hf_method, list_post_hf_methods, recommend_post_hf_method
from .methods.excited import get_excited_method, list_excited_methods, recommend_excited_method
from .methods.solvation import get_solvent, list_solvents, recommend_solvent
from .methods.casscf import recommend_casscf_space
from .templates.pyscf_templates import PySCFTemplateEngine
from .templates.base import GeneratedCode
from .core.executor import PySCFExecutor, ExecutionResult
from .core.parser import PySCFOutputParser
from .core.diagnostics import DiagnosticsEngine, format_diagnostics
from .core.interpreter import ResultInterpreter
from .config import get_api_key


@dataclass
class SessionContext:
    """Persistent session state across interactive queries."""
    last_molecule: Optional[str] = None
    last_method: Optional[str] = None
    last_basis: Optional[str] = None
    last_calc_type: Optional[str] = None
    recent_molecules: list[str] = field(default_factory=list)

    def update(self, intent: "ParsedIntent") -> None:
        """Update session state from a parsed intent."""
        if intent.molecule:
            self.last_molecule = intent.molecule
            if intent.molecule not in self.recent_molecules:
                self.recent_molecules.insert(0, intent.molecule)
                self.recent_molecules = self.recent_molecules[:5]
        if intent.method:
            self.last_method = intent.method
        if intent.basis:
            self.last_basis = intent.basis
        if intent.calc_type:
            self.last_calc_type = intent.calc_type


@dataclass
class ParsedIntent:
    molecule: Optional[str] = None
    method: Optional[str] = None
    basis: Optional[str] = None
    calc_type: Optional[str] = None
    solvent: Optional[str] = None
    n_states: Optional[int] = None
    norb: Optional[int] = None
    nelec: Optional[int] = None
    accuracy: str = "medium"
    output_file: Optional[str] = None
    confidence: float = 0.0
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


CALC_TYPE_KEYWORDS = {
    "energy": ["能量", "单点", "单点能", "energy", "single point"],
    "geometry": ["优化", "几何优化", "结构优化", "optimization", "optimize", "geom"],
    "frequency": ["频率", "振动", "热力学", "frequency", "freq", "vibration", "thermo"],
    "excited": ["激发", "激发态", "光谱", "吸收", "TDDFT", "excited", "spectrum", "absorption"],
    "casscf": ["CASSCF", "活性空间", "多参考", "multireference", "active space"],
    "nbo": ["NBO", "布居", "电荷", "population", "charge"],
    "solvation": ["溶剂", "溶剂化", "solvation", "solvent", "PCM", "SMD"],
}

METHOD_KEYWORDS = {
    "HF": ["HF", "Hartree-Fock", "hartree fock"],
    "B3LYP": ["B3LYP", "b3lyp"],
    "PBE": ["PBE", "pbe"],
    "PBE0": ["PBE0", "pbe0"],
    "M06-2X": ["M06-2X", "m062x", "M062X"],
    "wB97X-D": ["wB97X-D", "wb97x-d", "wb97xd", "WB97X-D"],
    "CAM-B3LYP": ["CAM-B3LYP", "cam-b3lyp"],
    "HSE06": ["HSE06", "hse06", "HSE"],
    "MP2": ["MP2", "mp2"],
    "CCSD": ["CCSD", "ccsd"],
    "CCSD(T)": ["CCSD(T)", "ccsd(t)", "CCSD-T", "ccsd-t", "CCSDT"],
    "TDDFT": ["TDDFT", "td-dft", "TD-DFT", "td_dft"],
    "CASSCF": ["CASSCF", "casscf"],
    "NEVPT2": ["NEVPT2", "nevpt2"],
    "CASPT2": ["CASPT2", "caspt2"],
}

BASIS_KEYWORDS = {
    "sto-3g": ["STO-3G", "sto-3g", "STO3G"],
    "3-21g": ["3-21G", "3-21g"],
    "6-31g*": ["6-31G*", "6-31g*", "6-31G(d)", "6-31g(d)", "6-31Gd"],
    "6-31g**": ["6-31G**", "6-31g**", "6-31G(d,p)", "6-31g(d,p)"],
    "6-31+g*": ["6-31+G*", "6-31+g*", "6-31+G(d)", "6-31+g(d)"],
    "6-31++g**": ["6-31++G**", "6-31++g**", "6-31++G(d,p)", "6-31++g(d,p)"],
    "6-311g**": ["6-311G**", "6-311g**", "6-311G(d,p)", "6-311g(d,p)"],
    "cc-pvdz": ["cc-pVDZ", "cc-pvdz", "ccpvdz", "CC-PVDZ"],
    "cc-pvtz": ["cc-pVTZ", "cc-pvtz", "ccpvtz", "CC-PVTZ"],
    "cc-pvqz": ["cc-pVQZ", "cc-pvqz", "ccpvqz", "CC-PVQZ"],
    "aug-cc-pvdz": ["aug-cc-pVDZ", "aug-cc-pvdz", "aug-cc-pvdz"],
    "aug-cc-pvtz": ["aug-cc-pVTZ", "aug-cc-pvtz", "aug-cc-pvtz"],
    "def2-svp": ["def2-SVP", "def2-svp", "def2svp"],
    "def2-tzvp": ["def2-TZVP", "def2-tzvp", "def2tzvp"],
}

SOLVENT_KEYWORDS = {
    "water": ["水", "water", "H2O"],
    "methanol": ["甲醇", "methanol", "MeOH"],
    "ethanol": ["乙醇", "ethanol", "EtOH"],
    "acetone": ["丙酮", "acetone"],
    "dmso": ["DMSO", "dmso", "二甲亚砜"],
    "dichloromethane": ["二氯甲烷", "DCM", "dichloromethane", "CH2Cl2"],
    "chloroform": ["氯仿", "chloroform", "CHCl3"],
    "thf": ["THF", "thf", "四氢呋喃"],
    "acetonitrile": ["乙腈", "acetonitrile", "MeCN"],
    "toluene": ["甲苯", "toluene"],
    "benzene": ["苯", "benzene"],
    "cyclohexane": ["环己烷", "cyclohexane"],
}


CHEMISTRY_KEYWORDS = [
    "计算", "算", "能量", "优化", "频率", "激发", "光谱", "溶剂", "活性空间",
    "基组", "泛函", "单点", "几何", "振动", "热力学", "吸收", "电荷", "布居",
    "calculate", "compute", "energy", "optimize", "frequency", "excited",
    "spectrum", "solvent", "basis", "functional", "geometry", "vibration",
    "smiles", "xyz", "import", "search", "workflow", "run",
    "hf", "b3lyp", "pbe", "mp2", "ccsd", "tddft", "casscf",
    "6-31g", "cc-pvdz", "cc-pvtz", "def2",
    "pcm", "smd", "dft", "scf",
]

GREETING_KEYWORDS = [
    "你好", "您好", "hi", "hello", "hey", "早上好", "下午好", "晚上好",
    "谢谢", "感谢", "thanks", "thank you", "bye", "再见", "拜拜",
]


class FrankAgent:

    def __init__(self, work_dir: Optional[str] = None, timeout: int = 600):
        self.engine = PySCFTemplateEngine()
        self.executor = PySCFExecutor(work_dir=work_dir, timeout=timeout)
        self.parser = PySCFOutputParser()
        self.diagnostics = DiagnosticsEngine()
        self.interpreter = ResultInterpreter()
        self.session = SessionContext()

    def parse_intent(self, text: str, use_session: bool = True) -> ParsedIntent:
        intent = ParsedIntent()
        text_lower = text.lower()

        # Stage 1: Attempt LLM-powered intent parsing
        llm_result = None
        if get_api_key():
            from .llm import parse_intent_with_llm
            llm_result = parse_intent_with_llm(text)

        if llm_result and llm_result.get("molecule"):
            # Use LLM result as primary source
            intent.molecule = llm_result.get("molecule")
            intent.method = llm_result.get("method")
            intent.basis = llm_result.get("basis")
            intent.calc_type = llm_result.get("calc_type")
            intent.solvent = llm_result.get("solvent")
            intent.n_states = llm_result.get("n_states")
            intent.norb = llm_result.get("norb")
            intent.nelec = llm_result.get("nelec")
            intent.accuracy = llm_result.get("accuracy", "medium")
            # Resolve molecule through the standard pipeline to get canonical name
            resolved = self._resolve_molecule_name(intent.molecule)
            if resolved:
                intent.molecule = resolved
            intent.confidence = min(1.0, llm_result.get("confidence", 0.8) + 0.1)
        else:
            # Stage 2: Fall back to keyword-based extraction
            intent.molecule = self._extract_molecule(text, text_lower)

            if not intent.molecule:
                smiles = self._extract_smiles(text)
                if smiles:
                    intent.molecule = self._register_smiles_molecule(smiles)

            if not intent.molecule:
                intent.molecule = self._resolve_external_molecule(text)

            intent.calc_type = self._extract_calc_type(text, text_lower)
            intent.method = self._extract_method(text, text_lower)
            intent.basis = self._extract_basis(text, text_lower)
            intent.solvent = self._extract_solvent(text, text_lower)
            intent.n_states = self._extract_n_states(text)
            intent.norb, intent.nelec = self._extract_casscf_space(text)

        # Apply session context for missing fields
        if use_session:
            self._apply_session_defaults(intent)

        self._infer_defaults(intent)
        if llm_result is None:
            intent.confidence = self._calculate_confidence(intent)

        return intent

    def _resolve_molecule_name(self, name: str) -> Optional[str]:
        """Resolve a molecule name through the standard pipeline.

        Returns the canonical molecule name or None.
        """
        # Try direct lookup
        try:
            get_molecule(name)
            return name
        except KeyError:
            pass

        # Try Chinese alias
        cn_aliases = {
            "水": "h2o", "氨": "nh3", "甲烷": "ch4", "乙烯": "c2h4",
            "乙炔": "c2h2", "苯": "c6h6", "甲醛": "h2co", "甲醇": "ch3oh",
            "乙醇": "c2h5oh", "乙酸": "ch3cooh", "丙酮": "ch3coch3",
            "二氧化碳": "co2", "一氧化碳": "co", "氮气": "n2",
            "氧气": "o2", "氢气": "h2", "氟化氢": "hf", "氯化氢": "hcl",
        }
        if name.lower() in cn_aliases:
            return cn_aliases[name.lower()]

        # Try molecular formula
        try:
            mol = get_molecule(name.lower().replace(" ", ""))
            return mol.name
        except KeyError:
            pass

        # Try external resolution (PubChem)
        try:
            mol = resolve_molecule(name)
            if mol:
                register_molecule(mol)
                return mol.name
        except Exception:
            pass

        return None

    def _apply_session_defaults(self, intent: ParsedIntent) -> None:
        """Fill missing intent fields from session context."""
        if not intent.molecule and self.session.last_molecule:
            intent.molecule = self.session.last_molecule
            intent.warnings.append(
                f"Reusing molecule from previous query: {self.session.last_molecule}"
            )
        if not intent.method and self.session.last_method:
            intent.method = self.session.last_method
            intent.warnings.append(
                f"Reusing method from previous query: {self.session.last_method}"
            )
        if not intent.basis and self.session.last_basis:
            intent.basis = self.session.last_basis
            intent.warnings.append(
                f"Reusing basis set from previous query: {self.session.last_basis}"
            )

    def _extract_molecule(self, text: str, text_lower: str) -> Optional[str]:
        cn_aliases = {
            "水分子": "h2o", "水": "h2o",
            "氨分子": "nh3", "氨": "nh3",
            "甲烷": "ch4", "乙烯": "c2h4",
            "乙炔": "c2h2", "苯": "c6h6",
            "甲醛": "h2co", "甲醇": "ch3oh",
            "乙醇": "c2h5oh", "乙酸": "ch3cooh", "丙酮": "ch3coch3",
            "二氧化碳": "co2", "一氧化碳": "co",
            "氮气": "n2", "氮分子": "n2",
            "氧气": "o2", "氢气": "h2",
            "氟化氢": "hf", "氯化氢": "hcl", "硫化氢": "h2s",
            "吡啶": "c5h5n", "环己烷": "cyclohexane",
            "乙烷": "c2h6", "丙烷": "c3h8",
            "过氧化氢": "h2o2", "臭氧": "o3",
            "二氧化硫": "so2", "氰化氢": "hcn", "硝酸": "hno3",
            "甲胺": "ch3nh2", "二甲醚": "ch3och3", "甲酸": "hcooh",
            "氯仿": "chcl3", "二氯甲烷": "ch2cl2", "四氯化碳": "ccl4",
        }

        for alias, mol_name in sorted(cn_aliases.items(), key=lambda x: -len(x[0])):
            if alias in text:
                return mol_name

        exclude_words = {"hf", "rhf", "uhf", "rohf", "mp2", "ccsd", "tddft", "casscf",
                         "b3lyp", "pbe", "pbe0", "sto-3g", "6-31g", "cc-pvdz", "cc-pvtz"}

        for mol in list_molecules():
            if len(mol.name) >= 2 and mol.name in text_lower:
                idx = text_lower.find(mol.name)
                if idx >= 0:
                    before = text_lower[idx-1] if idx > 0 else " "
                    after = text_lower[idx + len(mol.name)] if idx + len(mol.name) < len(text_lower) else " "
                    if not before.isalnum() and not after.isalnum():
                        if mol.name not in exclude_words:
                            return mol.name

            if len(mol.formula) >= 3 and mol.formula in text:
                return mol.name

        return None

    def _extract_calc_type(self, text: str, text_lower: str) -> Optional[str]:
        for calc_type, keywords in CALC_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return calc_type
        return None

    def _extract_method(self, text: str, text_lower: str) -> Optional[str]:
        for method, keywords in sorted(METHOD_KEYWORDS.items(), key=lambda x: -len(x[0])):
            for kw in keywords:
                if kw.lower() in text_lower:
                    return method
        return None

    def _extract_basis(self, text: str, text_lower: str) -> Optional[str]:
        for basis, keywords in BASIS_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return basis
        return None

    def _extract_solvent(self, text: str, text_lower: str) -> Optional[str]:
        solvent_context_keywords = ["溶剂", "溶剂化", "solvent", "solvation", "溶液"]
        has_solvent_context = any(kw in text for kw in solvent_context_keywords)

        if not has_solvent_context:
            return None

        for solvent, keywords in SOLVENT_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return solvent
        return None

    def _extract_n_states(self, text: str) -> Optional[int]:
        patterns = [
            r'(\d+)\s*个\s*激发',
            r'(\d+)\s*激发态',
            r'(\d+)\s*states',
            r'n\s*=\s*(\d+)',
            r'(\d+)\s*excited',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _extract_casscf_space(self, text: str) -> tuple[Optional[int], Optional[int]]:
        patterns = [
            r'\((\d+)\s*,\s*(\d+)\)',
            r'(\d+)\s*轨道\s*(\d+)\s*电子',
            r'norb\s*=\s*(\d+).*nelec\s*=\s*(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1)), int(match.group(2))
        return None, None

    def _extract_smiles(self, text: str) -> Optional[str]:
        import re

        smiles_patterns = [
            r'smiles\s*[=:]\s*([A-Za-z0-9@+\-\[\]\(\)=#/:\\]+)',
            r'SMILES\s*[=:]\s*([A-Za-z0-9@+\-\[\]\(\)=#/:\\]+)',
        ]

        for pattern in smiles_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        text_stripped = text.strip()
        if (len(text_stripped) > 2 and
            len(text_stripped) < 100 and
            not any('一' <= c <= '鿿' for c in text_stripped) and
            re.match(r'^[A-Za-z0-9@+\-\[\]\(\)=#/:\\]+$', text_stripped)):
            smiles_chars = set('()=#@/\\[]')
            if any(c in smiles_chars for c in text_stripped):
                return text_stripped

        return None

    def _register_smiles_molecule(self, smiles: str) -> Optional[str]:
        try:
            from .molecules.utils import smiles_to_molecule
            from .molecules.database import MOLECULES

            mol = smiles_to_molecule(smiles)
            if mol:
                MOLECULES[mol.name] = mol
                return mol.name
        except Exception:
            pass
        return None

    def _resolve_external_molecule(self, text: str) -> Optional[str]:
        candidates = self._extract_molecule_candidates(text)

        for candidate in candidates:
            try:
                mol = resolve_molecule(candidate)
                if mol:
                    register_molecule(mol)
                    return mol.name
            except Exception:
                continue

        cn_to_en = self._translate_chemical_names(text)
        for en_name in cn_to_en:
            try:
                mol = resolve_molecule(en_name)
                if mol:
                    register_molecule(mol)
                    return mol.name
            except Exception:
                continue

        return None

    def _translate_chemical_names(self, text: str) -> list[str]:
        cn_en_map = {
            "咖啡因": "caffeine",
            "阿司匹林": "aspirin",
            "布洛芬": "ibuprofen",
            "葡萄糖": "glucose",
            "果糖": "fructose",
            "蔗糖": "sucrose",
            "尿素": "urea",
            "苯甲酸": "benzoic acid",
            "对乙酰氨基酚": "acetaminophen",
            "尼古丁": "nicotine",
            "胆固醇": "cholesterol",
            "甘氨酸": "glycine",
            "丙氨酸": "alanine",
            "苯胺": "aniline",
            "萘": "naphthalene",
            "蒽": "anthracene",
            "吡咯": "pyrrole",
            "呋喃": "furan",
            "噻吩": "thiophene",
            "咪唑": "imidazole",
            "嘧啶": "pyrimidine",
            "吲哚": "indole",
            "喹啉": "quinoline",
            "嘌呤": "purine",
            "腺嘌呤": "adenine",
            "鸟嘌呤": "guanine",
            "胞嘧啶": "cytosine",
            "胸腺嘧啶": "thymine",
            "尿嘧啶": "uracil",
        }

        results = []
        for cn, en in cn_en_map.items():
            if cn in text:
                results.append(en)

        return results

    def _extract_molecule_candidates(self, text: str) -> list[str]:
        candidates = []

        noise_words = {
            "计算", "算", "帮忙", "帮我", "请", "please", "calculate", "compute",
            "用", "使用", "using", "with", "在", "at",
            "的能量", "能量", "单点", "单点能", "energy",
            "优化", "几何优化", "optimization", "optimize",
            "频率", "振动", "frequency", "freq",
            "激发", "激发态", "光谱", "excited",
            "的", "了", "和", "与", "the", "of", "for",
            "水平", "方法", "基组", "溶剂", "溶剂化",
            "B3LYP", "HF", "MP2", "CCSD", "TDDFT", "CASSCF",
            "6-31G", "cc-pVDZ", "cc-pVTZ", "def2-SVP", "def2-TZVP",
            "STO-3G", "6-311G", "aug-cc-pVDZ",
            "PCM", "SMD", "water", "methanol", "ethanol",
            "run", "ask",
        }

        cleaned = text
        for word in sorted(noise_words, key=len, reverse=True):
            cleaned = cleaned.replace(word, " ")

        for part in cleaned.split():
            part = part.strip("，。、；：“”‘’()（）[]【】")
            if len(part) >= 2 and not part.replace(".", "").replace("-", "").isdigit():
                candidates.append(part)

        stripped = text.strip()
        if stripped and stripped not in candidates:
            candidates.append(stripped)

        return candidates

    def _infer_defaults(self, intent: ParsedIntent):
        if not intent.molecule:
            intent.warnings.append(
                "No molecule identified. Supported inputs: built-in name, SMILES string, "
                "XYZ file path, or PubChem molecule name. Use 'search <name>' to query PubChem."
            )

        if not intent.calc_type:
            method_lower = (intent.method or "").lower()
            if "tddft" in method_lower or "td-dft" in method_lower:
                intent.calc_type = "excited"
            elif "casscf" in method_lower:
                intent.calc_type = "casscf"
            else:
                intent.calc_type = "energy"

        if not intent.method:
            if intent.calc_type == "excited":
                intent.method = "B3LYP"
            elif intent.calc_type == "casscf":
                intent.method = "CASSCF"
            elif intent.calc_type in ["energy", "geometry", "frequency"]:
                intent.method = "B3LYP"
            else:
                intent.method = "B3LYP"

        if not intent.basis:
            has_diffuse = intent.calc_type == "excited"
            intent.basis = recommend_basis_set(
                intent.method,
                intent.calc_type,
                intent.accuracy,
                has_diffuse,
            )

        if intent.calc_type == "excited" and intent.n_states is None:
            intent.n_states = 6

        if intent.calc_type == "casscf" and (intent.norb is None or intent.nelec is None):
            if intent.molecule:
                try:
                    mol = get_molecule(intent.molecule)
                    intent.norb, intent.nelec = recommend_casscf_space(
                        mol.electrons or 10, mol.name
                    )
                except:
                    intent.norb, intent.nelec = 4, 4
            else:
                intent.norb, intent.nelec = 4, 4

        if intent.solvent and intent.calc_type == "solvation":
            intent.calc_type = "energy"

    def _calculate_confidence(self, intent: ParsedIntent) -> float:
        score = 0.0
        total = 0.0

        if intent.molecule:
            score += 1.0
        total += 1.0

        if intent.method:
            score += 1.0
        total += 1.0

        if intent.basis:
            score += 0.5
        total += 0.5

        if intent.calc_type:
            score += 0.5
        total += 0.5

        return score / total if total > 0 else 0.0

    def generate_code(self, intent: ParsedIntent) -> GeneratedCode:
        if not intent.molecule:
            raise ValueError("请指定分子名称")

        return self.engine.generate_custom(
            mol_name=intent.molecule,
            method=intent.method or "B3LYP",
            basis=intent.basis or "6-31g*",
            calc_type=intent.calc_type or "energy",
            solvent=intent.solvent,
            n_states=intent.n_states or 6,
            norb=intent.norb or 4,
            nelec=intent.nelec or 4,
            output_file=intent.output_file,
        )

    def _is_chemistry_query(self, text: str) -> bool:
        text_lower = text.lower()
        for kw in CHEMISTRY_KEYWORDS:
            if kw in text_lower:
                return True
        for kw in GREETING_KEYWORDS:
            if kw in text_lower:
                return False
        for mol in list_molecules():
            if len(mol.name) >= 2 and mol.name in text_lower:
                return True
        if self._extract_smiles(text):
            return True
        return False

    def _chat_reply(self, text: str) -> str:
        # Try LLM first for natural conversational response
        if get_api_key():
            from .llm import chat_reply_with_llm
            llm_reply = chat_reply_with_llm(text)
            if llm_reply:
                return llm_reply

        # Fallback: hardcoded templates (used when LLM is unavailable)
        text_lower = text.lower().strip()
        if any(kw in text_lower for kw in ["你好", "您好", "hi", "hello", "hey"]):
            return (
                "Hello. I am Frank, a computational chemistry terminal agent. "
                "Please describe your calculation request. Examples:\n"
                "  - Calculate the energy of water at B3LYP/6-31G* level\n"
                "  - Optimize ammonia geometry with MP2/cc-pVDZ\n"
                "  - search caffeine (query PubChem)\n"
                "Type 'help' for complete usage information."
            )
        if any(kw in text_lower for kw in ["谢谢", "感谢", "thanks"]):
            return "You are welcome. Enter a calculation request when ready."
        if any(kw in text_lower for kw in ["再见", "拜拜", "bye"]):
            return "Session ended."
        return (
            "I am a computational chemistry assistant. "
            "Please provide a molecule name and calculation type. Examples:\n"
            "  - Calculate the energy of water at B3LYP/6-31G* level\n"
            "  - search caffeine (query PubChem)\n"
            "Type 'help' for complete usage information."
        )

    def process_request(self, text: str) -> dict:
        if not self._is_chemistry_query(text):
            return {
                "intent": ParsedIntent(),
                "code": None,
                "script": "",
                "is_chat": True,
                "chat_message": self._chat_reply(text),
                "warnings": [],
            }

        intent = self.parse_intent(text)

        code = None
        if intent.molecule:
            try:
                code = self.generate_code(intent)
                self.session.update(intent)
            except Exception as e:
                intent.warnings.append(f"Code generation failed: {str(e)}")

        script = code.to_script() if code else ""

        return {
            "intent": intent,
            "code": code,
            "script": script,
            "warnings": intent.warnings,
        }

    def run(self, text: str, interpret: bool = True) -> dict:
        intent = self.parse_intent(text)

        code = None
        if intent.molecule:
            try:
                code = self.generate_code(intent)
                self.session.update(intent)
            except Exception as e:
                intent.warnings.append(f"Code generation failed: {str(e)}")

        if not code:
            return {
                "intent": intent,
                "code": None,
                "script": "",
                "execution": None,
                "parsed": {},
                "diagnostics": [],
                "interpretation": "",
                "retry_log": [],
                "warnings": intent.warnings,
            }

        script = code.to_script()

        mol = get_molecule(intent.molecule)
        job_name = f"{mol.name}_{intent.method or 'b3lyp'}".lower()
        execution, retry_log = self.executor.execute_with_recovery(
            script, job_name, original_basis=intent.basis
        )

        parsed = {}
        plain_language = ""
        if execution.success:
            parsed = self.parser.parse_from_stdout(execution.stdout)

            import glob
            log_files = glob.glob(f"{execution.output_dir}/*.log")
            for log_file in log_files:
                log_parsed = self.parser.parse_from_file(log_file)
                parsed.update(log_parsed)

        diagnostics = []
        if execution.error_type:
            diagnostics.extend(self.diagnostics.diagnose_scf_convergence(
                execution.stdout
            ))
            # Get plain-language explanation for the error
            from .core.executor_common import classify_error
            _, _, plain_language = classify_error(execution.stderr, execution.stdout)

        interpretation = ""
        if interpret and parsed:
            interpretation = self.interpreter.interpret(
                parsed,
                method=intent.method or "HF",
                mol_name=mol.name_cn,
            )

        return {
            "intent": intent,
            "code": code,
            "script": script,
            "execution": execution,
            "parsed": parsed,
            "diagnostics": diagnostics,
            "interpretation": interpretation,
            "retry_log": retry_log,
            "warnings": intent.warnings,
            "plain_language": plain_language,
        }

    def run_workflow(
        self,
        molecule: str,
        workflow_type: str = "opt_freq",
        method: str = "B3LYP",
        basis: str = "6-31g*",
        **kwargs
    ):
        from .workflows.engine import WorkflowEngine

        workflow_engine = WorkflowEngine(executor=self.executor)

        if workflow_type == "opt_freq":
            return workflow_engine.run_geometry_optimization_frequency(
                molecule, method, basis, **kwargs
            )
        elif workflow_type == "method_comparison":
            methods = kwargs.get("methods", ["HF", "B3LYP", "MP2"])
            return workflow_engine.run_method_comparison(
                molecule, methods, basis
            )
        elif workflow_type == "basis_convergence":
            basis_sets = kwargs.get("basis_sets", ["6-31g*", "cc-pvdz", "cc-pvtz"])
            return workflow_engine.run_basis_set_convergence(
                molecule, method, basis_sets
            )
        elif workflow_type == "pes_scan":
            atoms_str = kwargs.get("atoms", "0,1")
            if isinstance(atoms_str, str):
                atom_indices = tuple(int(x) for x in atoms_str.split(","))
            else:
                atom_indices = atoms_str
            return workflow_engine.run_pes_scan(
                molecule,
                scan_type=kwargs.get("scan_type", "bond"),
                atom_indices=atom_indices,
                method=method,
                basis=basis,
                n_points=kwargs.get("n_points", 11),
                range_start=kwargs.get("range_start", 0.8),
                range_end=kwargs.get("range_end", 2.0),
            )
        elif workflow_type == "solvation":
            solvent = kwargs.get("solvent", "water")
            return workflow_engine.run_solvation_free_energy(
                molecule, method, basis, solvent
            )
        else:
            raise ValueError(f"未知工作流类型: {workflow_type}")

    def adjust_intent(self, intent: ParsedIntent, overrides: dict) -> ParsedIntent:
        """Create a new ParsedIntent with specified fields overridden.

        Args:
            intent: The original parsed intent.
            overrides: Dict mapping field names to new values.

        Returns:
            A new ParsedIntent with overrides applied.
        """
        new_intent = ParsedIntent(
            molecule=overrides.get("molecule", intent.molecule),
            method=overrides.get("method", intent.method),
            basis=overrides.get("basis", intent.basis),
            calc_type=overrides.get("calc_type", intent.calc_type),
            solvent=overrides.get("solvent", intent.solvent),
            n_states=overrides.get("n_states", intent.n_states),
            norb=overrides.get("norb", intent.norb),
            nelec=overrides.get("nelec", intent.nelec),
            accuracy=overrides.get("accuracy", intent.accuracy),
            output_file=overrides.get("output_file", intent.output_file),
            confidence=intent.confidence,
            warnings=list(intent.warnings),
        )
        return new_intent

    def get_help(self) -> str:
        return """
Frank -- Computational Chemistry Terminal Agent

Usage:
  Describe your calculation request in natural language. Examples:
  - "Calculate the energy of water at B3LYP/6-31G* level"
  - "Optimize ammonia geometry with MP2/cc-pVDZ"
  - "Compute benzene TDDFT excited states (6 states)"
  - "Run CASSCF(6,6)/cc-pVDZ on nitrogen"
  - "Calculate solvation energy of ethanol in water"

Molecule input:
  - Built-in names: use 'frank list molecules' to browse
  - PubChem lookup: 'frank search <name>' or use the name directly in a query
  - XYZ files: 'frank import <file.xyz>' or provide the file path directly
  - SMILES strings: enter directly (e.g., CCO, c1ccccc1)

Supported methods:
  - HF, RHF, UHF
  - DFT: B3LYP, PBE, PBE0, M06-2X, wB97X-D, CAM-B3LYP, HSE06
  - Post-HF: MP2, CCSD, CCSD(T)
  - Excited state: TDDFT, CIS, EOM-CCSD
  - Multi-reference: CASSCF, NEVPT2, CASPT2

Supported basis sets:
  - Split-valence: 6-31G*, 6-311G**
  - Correlation-consistent: cc-pVDZ, cc-pVTZ, aug-cc-pVDZ
  - Ahlrichs: def2-SVP, def2-TZVP
  - Minimal: STO-3G

Workflow aliases:
  - of -> opt_freq, mc/compare -> method_comparison
  - bc/converge -> basis_convergence, pes -> pes_scan
  - solv -> solvation
"""
