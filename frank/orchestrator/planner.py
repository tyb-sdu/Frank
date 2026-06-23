"""Workflow planner — decompose natural language into multi-step computational tasks."""

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from ..config import get_api_key


@dataclass
class WorkflowTask:
    """A single sub-task within a planned workflow."""
    agent: str
    description: str
    molecule: Optional[str] = None
    molecules: list[str] = field(default_factory=list)
    method: str = "B3LYP"
    basis: str = "6-31g*"
    coefficients: list[int] = field(default_factory=list)
    side: str = "reactant"  # reactant | product


@dataclass
class WorkflowPlan:
    """A complete multi-step workflow plan."""
    workflow_type: str
    title: str
    description: str
    tasks: list[WorkflowTask] = field(default_factory=list)
    method: str = "B3LYP"
    basis: str = "6-31g*"
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def is_complex(self) -> bool:
        return self.workflow_type != "single" and len(self.tasks) > 0


WORKFLOW_KEYWORDS = {
    "reaction_thermo": [
        "反应能", "反应焓", "反应热", "反应自由能", "热力学",
        "reaction energy", "reaction enthalpy", "reaction free energy",
        "thermochemistry", "diels-alder", "diels alder", "加成反应",
        "claisen", "克莱森", "质子亲和", "proton affinity",
        "atomization", "原子化能", "结合能", "binding energy",
    ],
    "tautomer": [
        "互变异构", "tautomer", "酮烯醇", "keto-enol", "keto enol",
        "哪个更稳定", "稳定性比较",
    ],
    "conjugation": [
        "共轭", "conjugation", "红移", "red shift", "吸收比较",
        "uv比较", "uv-vis比较", "激发态比较",
    ],
    "opt_freq": [
        "优化后频率", "opt freq", "opt_freq", "优化和频率",
        "几何优化和频率", "optimize and frequency",
    ],
    "method_comparison": [
        "方法对比", "方法比较", "method comparison", "compare methods",
    ],
    "basis_convergence": [
        "基组收敛", "basis convergence", "收敛性测试",
    ],
    "conformer": [
        "构象", "conformer", "构象比较", "conformational",
        "氢键构象", "hydrogen-bonded conformer", "不同构象",
    ],
}

# Built-in reaction templates (Aitomia-style predefined workflows)
REACTION_TEMPLATES = {
    "diels_alder_cyclopentadiene_maleimide": {
        "title": "Diels-Alder: cyclopentadiene + maleimide",
        "reactants": [("cyclopentadiene", 1), ("maleimide", 1)],
        "products": [("diels_alder_adduct", 1)],
        "keywords": ["diels-alder", "diels alder", "环戊二烯", "马来酰亚胺", "maleimide"],
    },
    "water_formation": {
        "title": "2 H2 + O2 -> 2 H2O",
        "reactants": [("h2", 2), ("o2", 1)],
        "products": [("h2o", 2)],
        "keywords": ["生成水", "水的生成", "h2 o2", "氢氧反应"],
    },
    "ammonia_protonation": {
        "title": "NH3 proton affinity",
        "reactants": [("nh3", 1), ("h+", 1)],
        "products": [("nh4+", 1)],
        "keywords": ["氨质子亲和", "质子亲和能", "proton affinity ammonia", "nh3质子"],
    },
    "claisen_ethyl_acetate": {
        "title": "Claisen condensation: 2 ethyl acetate",
        "reactants": [("ethyl_acetate", 2)],
        "products": [("acetoacetic_ester", 1), ("ethanol", 1)],
        "keywords": ["claisen", "克莱森", "ethyl acetate", "乙酸乙酯"],
    },
}

# Known tautomer pairs for common molecules
TAUTOMER_PAIRS = {
    "acetaldehyde": ["ch3cho", "ethenol"],
    "乙醛": ["ch3cho", "ethenol"],
    "ch3cho": ["ch3cho", "ethenol"],
    "acetone": ["ch3coch3", "propen2ol"],
    "丙酮": ["ch3coch3", "propen2ol"],
    "ch3coch3": ["ch3coch3", "propen2ol"],
}

CONJUGATION_SERIES = {
    "default": ["c2h4", "butadiene", "hexatriene"],
    "conjugation": ["c2h4", "butadiene", "hexatriene"],
    "共轭": ["c2h4", "butadiene", "hexatriene"],
}


PLANNER_SYSTEM_PROMPT = """You are a computational chemistry workflow planner (inspired by Aitomia multi-agent architecture).
Analyze the user's request and return a JSON object with:
- workflow_type: one of "single", "reaction_thermo", "tautomer", "conjugation", "opt_freq", "method_comparison", "basis_convergence", "conformer"
- title: short title in the user's language
- description: what will be computed
- method: computational method (default B3LYP)
- basis: basis set (default 6-31g*)
- reactants: list of {"name": molecule, "coeff": stoichiometric coefficient}
- products: list of {"name": molecule, "coeff": stoichiometric coefficient}
- molecules: list of molecule names (for comparison/conjugation workflows)
- confidence: 0.0-1.0

Rules:
- For reaction energy/enthalpy queries, use workflow_type "reaction_thermo"
- For tautomer stability, use "tautomer" with molecules as different tautomers
- For UV/conjugation comparison, use "conjugation"
- For simple single-point/opt/freq, use "single"
- Use lowercase molecule names (h2o, benzene, nh3)
- Output ONLY valid JSON"""


class WorkflowPlanner:
    """Plan multi-step workflows from natural language (LLM + rule-based fallback)."""

    def plan(self, text: str) -> WorkflowPlan:
        rag_hints = self._retrieve_planning_hints(text)
        llm_plan = self._plan_with_llm(text, rag_hints)
        if llm_plan and llm_plan.confidence >= 0.6:
            if rag_hints:
                llm_plan.warnings.append(f"RAG hints applied: {len(rag_hints)} knowledge chunks.")
            return llm_plan
        rule_plan = self._plan_with_rules(text)
        if rag_hints and rule_plan.warnings is not None:
            rule_plan.warnings.append(f"RAG hints: {rag_hints[0][:80]}...")
        return rule_plan

    def _retrieve_planning_hints(self, text: str) -> list[str]:
        """Adaptive-RAG: pull workflow/method hints to guide planning."""
        try:
            from ..knowledge.base import KnowledgeRetriever
            retriever = KnowledgeRetriever()
            chunks = retriever.retrieve(text, top_k=3)
            return [c.content for c in chunks if c.category in ("workflow", "concept", "method")]
        except Exception:
            return []

    def _plan_with_llm(self, text: str, rag_hints: Optional[list[str]] = None) -> Optional[WorkflowPlan]:
        if not get_api_key():
            return None
        try:
            from openai import OpenAI
            from ..llm import get_base_url, get_model_name

            client = OpenAI(api_key=get_api_key(), base_url=get_base_url())
            user_content = text
            if rag_hints:
                user_content = (
                    "Relevant knowledge:\n" + "\n".join(rag_hints[:3])
                    + f"\n\nUser request: {text}"
                )
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            return self._build_plan_from_dict(data)
        except Exception:
            return None

    def _plan_with_rules(self, text: str) -> WorkflowPlan:
        text_lower = text.lower()

        # Match built-in reaction templates
        for tpl_id, tpl in REACTION_TEMPLATES.items():
            if any(kw in text_lower for kw in tpl["keywords"]):
                return self._reaction_plan(
                    tpl["title"],
                    tpl["reactants"],
                    tpl["products"],
                    confidence=0.85,
                )

        # Keyword-based workflow type detection
        for wf_type, keywords in WORKFLOW_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                if wf_type == "reaction_thermo":
                    return self._parse_reaction_from_text(text)
                if wf_type == "tautomer":
                    mols = self._extract_molecule_list(text)
                    if len(mols) >= 2:
                        return self._tautomer_plan(mols)
                    pair = self._resolve_tautomer_pair(text_lower)
                    if pair:
                        return self._tautomer_plan(pair)
                if wf_type == "conjugation":
                    mols = self._extract_molecule_list(text)
                    if len(mols) >= 2:
                        return self._conjugation_plan(mols)
                    series = self._resolve_conjugation_series(text_lower)
                    if series:
                        return self._conjugation_plan(series)
                if wf_type == "conformer":
                    mol = self._extract_single_molecule(text)
                    if mol:
                        return self._conformer_plan(mol, text)
                if wf_type == "opt_freq":
                    mol = self._extract_single_molecule(text)
                    if mol:
                        return self._opt_freq_plan(mol)
                if wf_type == "method_comparison":
                    mol = self._extract_single_molecule(text)
                    if mol:
                        return WorkflowPlan(
                            workflow_type="method_comparison",
                            title=f"Method comparison: {mol}",
                            description="Compare HF, B3LYP, MP2 single-point energies",
                            method="B3LYP",
                            basis="6-31g*",
                            tasks=[WorkflowTask(
                                agent="method_comparison",
                                description="Parallel method comparison",
                                molecule=mol,
                            )],
                            confidence=0.75,
                        )

        # Default: single calculation
        return WorkflowPlan(
            workflow_type="single",
            title="Single calculation",
            description="Standard single-step calculation",
            confidence=0.3,
        )

    def _build_plan_from_dict(self, data: dict) -> WorkflowPlan:
        wf_type = data.get("workflow_type", "single")
        method = data.get("method") or "B3LYP"
        basis = data.get("basis") or "6-31g*"
        confidence = float(data.get("confidence", 0.7))

        if wf_type == "reaction_thermo":
            reactants = [(r["name"], r.get("coeff", 1)) for r in data.get("reactants", [])]
            products = [(p["name"], p.get("coeff", 1)) for p in data.get("products", [])]
            if reactants and products:
                return self._reaction_plan(
                    data.get("title", "Reaction thermochemistry"),
                    reactants, products, method, basis, confidence,
                )

        if wf_type == "tautomer":
            mols = [m["name"] if isinstance(m, dict) else m for m in data.get("molecules", [])]
            if len(mols) >= 2:
                return self._tautomer_plan(mols, method, basis, confidence)

        if wf_type == "conjugation":
            mols = [m["name"] if isinstance(m, dict) else m for m in data.get("molecules", [])]
            if len(mols) >= 2:
                return self._conjugation_plan(mols, method, basis, confidence)

        if wf_type == "conformer":
            mols = data.get("molecules") or []
            mol = mols[0]["name"] if mols and isinstance(mols[0], dict) else (mols[0] if mols else None)
            if mol:
                return self._conformer_plan(mol, data.get("description", ""), method, basis, confidence)

        if wf_type == "opt_freq":
            mols = data.get("molecules") or []
            mol = mols[0]["name"] if mols and isinstance(mols[0], dict) else (mols[0] if mols else None)
            if mol:
                return self._opt_freq_plan(mol, method, basis, confidence)

        return WorkflowPlan(
            workflow_type="single",
            title=data.get("title", "Single calculation"),
            description=data.get("description", ""),
            method=method,
            basis=basis,
            confidence=confidence,
        )

    def _reaction_plan(
        self,
        title: str,
        reactants: list[tuple[str, int]],
        products: list[tuple[str, int]],
        method: str = "B3LYP",
        basis: str = "6-31g*",
        confidence: float = 0.8,
    ) -> WorkflowPlan:
        tasks = []
        for name, coeff in reactants:
            tasks.append(WorkflowTask(
                agent="opt_freq",
                description=f"Optimize + frequency: {name} (reactant ×{coeff})",
                molecule=name,
                method=method,
                basis=basis,
                coefficients=[coeff],
                side="reactant",
            ))
        for name, coeff in products:
            tasks.append(WorkflowTask(
                agent="opt_freq",
                description=f"Optimize + frequency: {name} (product ×{coeff})",
                molecule=name,
                method=method,
                basis=basis,
                coefficients=[coeff],
                side="product",
            ))
        tasks.append(WorkflowTask(
            agent="thermo_analysis",
            description="Compute ΔE, ΔH, ΔG for the reaction",
            method=method,
            basis=basis,
        ))
        return WorkflowPlan(
            workflow_type="reaction_thermo",
            title=title,
            description="Geometry optimization → frequency → reaction thermochemistry",
            tasks=tasks,
            method=method,
            basis=basis,
            confidence=confidence,
        )

    def _tautomer_plan(
        self,
        molecules: list[str],
        method: str = "B3LYP",
        basis: str = "6-31g*",
        confidence: float = 0.75,
    ) -> WorkflowPlan:
        tasks = []
        for mol in molecules:
            tasks.append(WorkflowTask(
                agent="opt_freq",
                description=f"Tautomer opt+freq: {mol}",
                molecule=mol,
                method=method,
                basis=basis,
                side="reactant",
            ))
        tasks.append(WorkflowTask(
            agent="tautomer_analysis",
            description="Compare relative stability of tautomers",
        ))
        return WorkflowPlan(
            workflow_type="tautomer",
            title=f"Tautomer comparison: {', '.join(molecules)}",
            description="Compare thermodynamic stability of tautomers",
            tasks=tasks,
            method=method,
            basis=basis,
            confidence=confidence,
        )

    def _conjugation_plan(
        self,
        molecules: list[str],
        method: str = "B3LYP",
        basis: str = "6-31g*",
        confidence: float = 0.75,
    ) -> WorkflowPlan:
        tasks = []
        for mol in molecules:
            tasks.append(WorkflowTask(
                agent="excited",
                description=f"TDDFT excited states: {mol}",
                molecule=mol,
                method=method,
                basis=basis,
            ))
        tasks.append(WorkflowTask(
            agent="conjugation_analysis",
            description="Analyze conjugation / red-shift trend",
        ))
        return WorkflowPlan(
            workflow_type="conjugation",
            title=f"Conjugation UV comparison: {', '.join(molecules)}",
            description="TDDFT comparison of absorption spectra",
            tasks=tasks,
            method=method,
            basis=basis,
            confidence=confidence,
        )

    def _conformer_plan(
        self,
        molecule: str,
        description: str = "",
        method: str = "B3LYP",
        basis: str = "6-31g*",
        confidence: float = 0.75,
    ) -> WorkflowPlan:
        n_conformers = 5
        if "10" in description or "十个" in description:
            n_conformers = 10
        return WorkflowPlan(
            workflow_type="conformer",
            title=f"Conformer search: {molecule}",
            description=f"RDKit conformer enumeration ({n_conformers} conformers) → opt+freq",
            tasks=[
                WorkflowTask(
                    agent="conformer_search",
                    description=f"Enumerate conformers for {molecule}",
                    molecule=molecule,
                    method=method,
                    basis=basis,
                    coefficients=[n_conformers],
                ),
            ],
            method=method,
            basis=basis,
            confidence=confidence,
        )

    def _resolve_conjugation_series(self, text_lower: str) -> list[str]:
        for key, series in CONJUGATION_SERIES.items():
            if key in text_lower:
                return series
        if "ethene" in text_lower or "butadiene" in text_lower or "hexatriene" in text_lower:
            return CONJUGATION_SERIES["default"]
        return []

    def _opt_freq_plan(
        self,
        molecule: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        confidence: float = 0.8,
    ) -> WorkflowPlan:
        return WorkflowPlan(
            workflow_type="opt_freq",
            title=f"Opt+Freq: {molecule}",
            description="Geometry optimization with frequency validation",
            tasks=[WorkflowTask(
                agent="opt_freq",
                description=f"Optimize + frequency: {molecule}",
                molecule=molecule,
                method=method,
                basis=basis,
            )],
            method=method,
            basis=basis,
            confidence=confidence,
        )

    def _parse_reaction_from_text(self, text: str) -> WorkflowPlan:
        """Parse reactants/products from arrow notation in text."""
        arrow_patterns = [r"\s*->\s*", r"\s*→\s*", r"\s*=>\s*", r"\s*⇌\s*", r"\s*\+\s*->\s*"]
        for pat in arrow_patterns:
            if re.search(pat, text):
                parts = re.split(pat, text, maxsplit=1)
                if len(parts) == 2:
                    reactants = self._parse_stoichiometry(self._clean_reaction_side(parts[0]))
                    products = self._parse_stoichiometry(self._clean_reaction_side(parts[1]))
                    if reactants and products:
                        return self._reaction_plan(
                            "User-defined reaction",
                            reactants, products,
                            confidence=0.7,
                        )
        return WorkflowPlan(
            workflow_type="reaction_thermo",
            title="Reaction thermochemistry",
            description="Could not parse reaction equation; please specify reactants and products",
            confidence=0.2,
            warnings=["Unable to parse reaction equation. Use format: reactants -> products"],
        )

    def _clean_reaction_side(self, side: str) -> str:
        """Strip descriptive text, keep only stoichiometric terms."""
        cleaned = re.sub(r"^.*[:：]\s*", "", side.strip())
        noise = [
            "计算", "反应能", "反应焓", "反应热", "求", "请", "the", "calculate",
            "reaction energy", "reaction enthalpy", "compute",
        ]
        for word in noise:
            cleaned = cleaned.replace(word, " ")
        return cleaned.strip()

    def _parse_stoichiometry(self, side: str) -> list[tuple[str, int]]:
        """Parse '2 h2 + o2' into [('h2', 2), ('o2', 1)]."""
        results = []
        for part in re.split(r"\s*\+\s*", side.strip()):
            part = part.strip()
            if not part:
                continue
            m = re.match(r"^(\d+)\s*(.+)$", part)
            if m:
                coeff = int(m.group(1))
                name = self._normalize_molecule_name(m.group(2))
            else:
                coeff = 1
                name = self._normalize_molecule_name(part)
            if name:
                results.append((name, coeff))
        return results

    def _extract_molecule_list(self, text: str) -> list[str]:
        known = [
            "h2o", "nh3", "ch4", "c2h4", "c2h2", "c6h6", "benzene",
            "ethene", "butadiene", "hexatriene", "ethanol", "methanol",
            "acetaldehyde", "ch3cho", "aniline", "naphthalene", "water", "ammonia",
            "salicylic", "salicylic_acid",
        ]
        text_lower = text.lower()
        found = []
        for mol in known:
            if mol in text_lower:
                canonical = {"water": "h2o", "ammonia": "nh3", "benzene": "c6h6",
                             "ethene": "c2h4"}.get(mol, mol)
                if canonical not in found:
                    found.append(canonical)
        return found

    def _extract_single_molecule(self, text: str) -> Optional[str]:
        mols = self._extract_molecule_list(text)
        return mols[0] if mols else None

    def _resolve_tautomer_pair(self, text_lower: str) -> list[str]:
        for key, pair in TAUTOMER_PAIRS.items():
            if key in text_lower:
                return pair
        return []

    def _normalize_molecule_name(self, name: str) -> str:
        name = name.strip().lower()
        aliases = {
            "水": "h2o", "water": "h2o", "h2o": "h2o",
            "氨": "nh3", "ammonia": "nh3", "nh3": "nh3",
            "苯": "c6h6", "benzene": "c6h6",
            "氢气": "h2", "h2": "h2",
            "氧气": "o2", "o2": "o2",
            "乙烯": "c2h4", "ethene": "c2h4",
            "乙炔": "c2h2",
            "甲烷": "ch4",
        }
        return aliases.get(name, re.sub(r"[^a-z0-9+\-]", "", name) or name)
