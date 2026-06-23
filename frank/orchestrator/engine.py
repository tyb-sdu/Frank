"""Orchestrator engine — execute multi-agent workflow plans autonomously."""

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..core.executor import PySCFExecutor
from ..core.interpreter import ResultInterpreter, HARTREE_TO_KCAL
from ..core.parser import PySCFOutputParser
from ..molecules.database import get_molecule
from ..molecules.sources import resolve_molecule, register_molecule
from ..workflows.engine import WorkflowEngine, WorkflowResult
from .planner import WorkflowPlan, WorkflowTask
from .self_correction import SelfCorrectionEngine, SelfCorrectionResult
from .stoichiometry import solve_stoichiometry, format_energy_delta


@dataclass
class SpeciesResult:
    name: str
    side: str
    coefficient: int
    correction: Optional[SelfCorrectionResult] = None
    electronic_energy: Optional[float] = None
    enthalpy: Optional[float] = None
    free_energy: Optional[float] = None


@dataclass
class OrchestratorResult:
    plan: WorkflowPlan
    workflow_result: Optional[WorkflowResult] = None
    species_results: list[SpeciesResult] = field(default_factory=list)
    summary: str = ""
    success: bool = False
    warnings: list[str] = field(default_factory=list)


class OrchestratorEngine:
    """Aitomia-style multi-agent orchestrator for Frank."""

    def __init__(self, executor: Optional[PySCFExecutor] = None, timeout: int = 600):
        self.executor = executor or PySCFExecutor(timeout=timeout)
        self.planner_engine = WorkflowEngine(executor=self.executor)
        self.correction = SelfCorrectionEngine(executor=self.executor)
        self.parser = PySCFOutputParser()
        self.interpreter = ResultInterpreter()

    def execute(
        self,
        plan: WorkflowPlan,
        progress_callback: Optional[Callable] = None,
    ) -> OrchestratorResult:
        if not plan.is_complex:
            return OrchestratorResult(
                plan=plan,
                success=False,
                warnings=["Not a complex workflow; use standard single-step calculation."],
            )

        handlers = {
            "reaction_thermo": self._execute_reaction_thermo,
            "tautomer": self._execute_tautomer,
            "conjugation": self._execute_conjugation,
            "conformer": self._execute_conformer,
            "opt_freq": self._execute_opt_freq,
            "method_comparison": self._execute_method_comparison,
            "basis_convergence": self._execute_basis_convergence,
        }
        handler = handlers.get(plan.workflow_type)
        if handler:
            return handler(plan, progress_callback)
        return OrchestratorResult(
            plan=plan,
            success=False,
            warnings=[f"Unsupported workflow type: {plan.workflow_type}"],
        )

    def _resolve_molecule(self, name: str) -> bool:
        try:
            get_molecule(name)
            return True
        except KeyError:
            pass
        try:
            mol = resolve_molecule(name)
            if mol:
                register_molecule(mol)
                return True
        except Exception:
            pass
        return False

    def _execute_reaction_thermo(
        self,
        plan: WorkflowPlan,
        progress_callback: Optional[Callable] = None,
    ) -> OrchestratorResult:
        result = OrchestratorResult(plan=plan)
        species_results = []

        opt_tasks = [t for t in plan.tasks if t.agent == "opt_freq"]

        # Aitomia-style deterministic stoichiometry from atom conservation
        reactant_names = [t.molecule for t in opt_tasks if t.side == "reactant" and t.molecule]
        product_names = [t.molecule for t in opt_tasks if t.side == "product" and t.molecule]
        stoich = solve_stoichiometry(reactant_names, product_names)
        coeff_map: dict[str, int] = {}
        if stoich.balanced:
            coeff_map = {n: c for n, c in stoich.reactants + stoich.products}
            result.warnings.append(
                "Stoichiometry determined deterministically via atom-conservation matrix."
            )
        elif stoich.error:
            result.warnings.append(f"Stoichiometry check: {stoich.error} — using planner coefficients.")

        total = len(opt_tasks)

        for i, task in enumerate(opt_tasks):
            if not self._resolve_molecule(task.molecule):
                result.warnings.append(f"Cannot resolve molecule: {task.molecule}")
                continue

            if progress_callback:
                progress_callback(
                    f"[{i+1}/{total}] {task.description}", "running", i, total
                )

            coeff = coeff_map.get(task.molecule) or (
                task.coefficients[0] if task.coefficients else 1
            )
            sc_result = self.correction.run_opt_freq_with_correction(
                task.molecule, task.method, task.basis, progress_callback
            )

            sr = SpeciesResult(
                name=task.molecule,
                side=task.side,
                coefficient=coeff,
                correction=sc_result,
            )

            if sc_result.opt_parsed.get("scf"):
                sr.electronic_energy = sc_result.opt_parsed["scf"].energy

            freq = sc_result.freq_parsed.get("frequency")
            if freq:
                sr.enthalpy = freq.enthalpy
                sr.free_energy = freq.free_energy
                if not sc_result.is_minimum:
                    result.warnings.append(
                        f"{task.molecule}: {freq.n_imaginary} imaginary frequency(ies) — "
                        "thermochemistry may be unreliable"
                    )

            species_results.append(sr)

        result.species_results = species_results
        result.summary = self._compute_reaction_thermo(species_results, plan.title)
        result.success = len(species_results) >= 2 and any(
            sr.correction and sr.correction.success for sr in species_results
        )
        return result

    def _compute_reaction_thermo(
        self,
        species: list[SpeciesResult],
        title: str,
    ) -> str:
        lines = [f"\n{'='*60}", f"  Reaction Thermochemistry: {title}", f"{'='*60}\n"]

        reactants = [s for s in species if s.side == "reactant"]
        products = [s for s in species if s.side == "product"]

        lines.append(f"{'Species':<20} {'Side':<10} {'E (Ha)':<18} {'H (Ha)':<18} {'G (Ha)':<18}")
        lines.append("-" * 84)

        for s in species:
            e = f"{s.electronic_energy:.10f}" if s.electronic_energy else "N/A"
            h = f"{s.enthalpy:.10f}" if s.enthalpy else "N/A"
            g = f"{s.free_energy:.10f}" if s.free_energy else "N/A"
            lines.append(f"{s.name:<20} {s.side:<10} {e:<18} {h:<18} {g:<18}")

        def _weighted_sum(items, attr):
            total = 0.0
            count = 0
            for s in items:
                val = getattr(s, attr)
                if val is not None:
                    total += val * s.coefficient
                    count += 1
            return total if count > 0 else None

        dE = dH = dG = None
        e_r = _weighted_sum(reactants, "electronic_energy")
        e_p = _weighted_sum(products, "electronic_energy")
        h_r = _weighted_sum(reactants, "enthalpy")
        h_p = _weighted_sum(products, "enthalpy")
        g_r = _weighted_sum(reactants, "free_energy")
        g_p = _weighted_sum(products, "free_energy")

        if e_r is not None and e_p is not None:
            dE = (e_p - e_r) * HARTREE_TO_KCAL
        if h_r is not None and h_p is not None:
            dH = (h_p - h_r) * HARTREE_TO_KCAL
        if g_r is not None and g_p is not None:
            dG = (g_p - g_r) * HARTREE_TO_KCAL

        lines.append(f"\n{'='*60}")
        lines.append("  Reaction Properties (products − reactants)")
        lines.append(f"{'='*60}")
        if e_r is not None and e_p is not None:
            dE_ha = e_p - e_r
            lines.append(f"  ΔE  = {format_energy_delta(dE_ha)}")
        elif dE is not None:
            lines.append(f"  ΔE  = {dE:+.4f} kcal/mol")
        if h_r is not None and h_p is not None:
            dH_ha = h_p - h_r
            lines.append(
                f"  ΔH  = {format_energy_delta(dH_ha)}  "
                "(298 K, ZPE + thermal corrections)"
            )
        elif dH is not None:
            lines.append(f"  ΔH  = {dH:+.4f} kcal/mol  (298 K, includes ZPE + thermal corrections)")
        if g_r is not None and g_p is not None:
            dG_ha = g_p - g_r
            lines.append(f"  ΔG  = {format_energy_delta(dG_ha)}  (298 K)")
        elif dG is not None:
            lines.append(f"  ΔG  = {dG:+.4f} kcal/mol  (298 K)")

        if dE is not None:
            if (e_r is not None and e_p is not None and (e_p - e_r) < 0) or dE < 0:
                lines.append("\n  Interpretation: Exothermic reaction (ΔE < 0)")
            else:
                lines.append("\n  Interpretation: Endothermic reaction (ΔE > 0)")

        # Self-correction log
        for s in species:
            if s.correction and s.correction.attempts:
                for att in s.correction.attempts:
                    if att.n_imaginary_before > 0:
                        status = "fixed" if att.success else "partial"
                        lines.append(
                            f"\n  [Self-correction] {s.name}: "
                            f"{att.n_imaginary_before} imag freq → {status}"
                        )

        return "\n".join(lines)

    def _execute_tautomer(
        self,
        plan: WorkflowPlan,
        progress_callback: Optional[Callable] = None,
    ) -> OrchestratorResult:
        result = OrchestratorResult(plan=plan)
        species_results = []

        opt_tasks = [t for t in plan.tasks if t.agent == "opt_freq"]
        for i, task in enumerate(opt_tasks):
            if not self._resolve_molecule(task.molecule):
                result.warnings.append(f"Cannot resolve molecule: {task.molecule}")
                continue
            if progress_callback:
                progress_callback(f"Tautomer {task.molecule}", "running", i, len(opt_tasks))
            sc = self.correction.run_opt_freq_with_correction(
                task.molecule, task.method, task.basis
            )
            sr = SpeciesResult(
                name=task.molecule, side="reactant", coefficient=1, correction=sc
            )
            if sc.freq_parsed.get("frequency"):
                sr.free_energy = sc.freq_parsed["frequency"].free_energy
                sr.enthalpy = sc.freq_parsed["frequency"].enthalpy
            if sc.opt_parsed.get("scf"):
                sr.electronic_energy = sc.opt_parsed["scf"].energy
            species_results.append(sr)

        result.species_results = species_results
        lines = [f"\n{'='*60}", f"  Tautomer Stability: {plan.title}", f"{'='*60}\n"]

        ranked = sorted(
            [(s.name, s.free_energy or s.electronic_energy) for s in species_results
             if s.free_energy or s.electronic_energy],
            key=lambda x: x[1],
        )
        if ranked:
            ref_name, ref_e = ranked[0]
            lines.append(f"Most stable: {ref_name} (G = {ref_e:.10f} Ha)")
            for name, e in ranked[1:]:
                dG = (e - ref_e) * HARTREE_TO_KCAL
                lines.append(f"  {name}: ΔG = {dG:+.4f} kcal/mol relative to {ref_name}")
        else:
            lines.append("Insufficient data for tautomer comparison.")

        result.summary = "\n".join(lines)
        result.success = len(species_results) >= 2
        return result

    def _execute_conformer(
        self,
        plan: WorkflowPlan,
        progress_callback: Optional[Callable] = None,
    ) -> OrchestratorResult:
        from ..molecules.conformers import search_conformers_for_molecule
        from ..molecules.sources import register_molecule

        result = OrchestratorResult(plan=plan)
        task = next((t for t in plan.tasks if t.agent == "conformer_search"), None)
        if not task or not task.molecule:
            result.warnings.append("No conformer search task in plan.")
            return result

        n_conformers = task.coefficients[0] if task.coefficients else 5
        if progress_callback:
            progress_callback(f"Searching conformers: {task.molecule}", "running")

        search = search_conformers_for_molecule(task.molecule, n_conformers)
        if search.error or not search.conformers:
            result.warnings.append(search.error or "No conformers generated.")
            return result

        lines = [f"\n{'='*60}", f"  Conformer Search: {plan.title}", f"{'='*60}\n"]
        species_results = []

        top_n = min(3, len(search.conformers))
        for i, conf in enumerate(search.conformers[:top_n]):
            register_molecule(conf.molecule)
            if progress_callback:
                progress_callback(
                    f"Opt+freq conformer {i+1}/{top_n}: {conf.label}", "running", i, top_n
                )
            sc = self.correction.run_opt_freq_with_correction(
                conf.molecule.name, task.method, task.basis
            )
            sr = SpeciesResult(
                name=conf.label, side="reactant", coefficient=1, correction=sc
            )
            if sc.freq_parsed.get("frequency"):
                sr.free_energy = sc.freq_parsed["frequency"].free_energy
                sr.enthalpy = sc.freq_parsed["frequency"].enthalpy
            if sc.opt_parsed.get("scf"):
                sr.electronic_energy = sc.opt_parsed["scf"].energy
            species_results.append(sr)
            e_str = f"{conf.energy:.2f}" if conf.energy else "N/A"
            g_str = f"{sr.free_energy:.10f}" if sr.free_energy else "N/A"
            lines.append(f"  {conf.label}: MMFF={e_str} kcal/mol, G={g_str} Ha")

        if species_results:
            ranked = sorted(
                [(s.name, s.free_energy or s.electronic_energy) for s in species_results
                 if s.free_energy or s.electronic_energy],
                key=lambda x: x[1],
            )
            if ranked:
                lines.append(f"\n  Lowest-energy conformer: {ranked[0][0]}")
                ref = ranked[0][1]
                for name, e in ranked[1:]:
                    dG = (e - ref) * HARTREE_TO_KCAL
                    lines.append(f"    {name}: ΔG = {dG:+.4f} kcal/mol")

        result.species_results = species_results
        result.summary = "\n".join(lines)
        result.success = len(species_results) >= 1
        return result

    def _execute_conjugation(
        self,
        plan: WorkflowPlan,
        progress_callback: Optional[Callable] = None,
    ) -> OrchestratorResult:
        from ..templates.pyscf_templates import PySCFTemplateEngine
        templates = PySCFTemplateEngine()
        result = OrchestratorResult(plan=plan)
        excited_tasks = [t for t in plan.tasks if t.agent == "excited"]
        lines = [f"\n{'='*60}", f"  Conjugation UV Comparison: {plan.title}", f"{'='*60}\n"]
        wavelengths = []

        for i, task in enumerate(excited_tasks):
            if not self._resolve_molecule(task.molecule):
                result.warnings.append(f"Cannot resolve: {task.molecule}")
                continue
            if progress_callback:
                progress_callback(f"TDDFT: {task.molecule}", "running", i, len(excited_tasks))
            code = templates.generate_custom(
                task.molecule, task.method, "6-31+g*", "excited", n_states=6
            )
            exec_result, _ = self.executor.execute_with_recovery(
                code.to_script(), f"{task.molecule}_tddft", original_basis="6-31+g*"
            )
            if exec_result.success:
                parsed = self.parser.parse_from_stdout(exec_result.stdout)
                tddft = parsed.get("tddft")
                if tddft and tddft.wavelengths:
                    wl = tddft.wavelengths[0]
                    wavelengths.append((task.molecule, wl))
                    lines.append(f"  {task.molecule}: λ_max = {wl:.1f} nm (S1)")

        if len(wavelengths) >= 2:
            lines.append("\n  Red-shift trend (longer λ = smaller gap):")
            for name, wl in sorted(wavelengths, key=lambda x: x[1], reverse=True):
                lines.append(f"    {name}: {wl:.1f} nm")

        result.summary = "\n".join(lines)
        result.success = len(wavelengths) >= 2
        return result

    def _execute_opt_freq(
        self,
        plan: WorkflowPlan,
        progress_callback: Optional[Callable] = None,
    ) -> OrchestratorResult:
        task = next((t for t in plan.tasks if t.agent == "opt_freq"), None)
        if not task:
            return OrchestratorResult(plan=plan, warnings=["No opt_freq task in plan"])
        wf = self.planner_engine.run_geometry_optimization_frequency(
            task.molecule, task.method, task.basis, progress_callback=progress_callback
        )
        return OrchestratorResult(
            plan=plan,
            workflow_result=wf,
            summary=wf.summary,
            success=wf.success,
        )

    def _execute_method_comparison(
        self,
        plan: WorkflowPlan,
        progress_callback: Optional[Callable] = None,
    ) -> OrchestratorResult:
        task = plan.tasks[0] if plan.tasks else None
        if not task:
            return OrchestratorResult(plan=plan, warnings=["No task in plan"])
        wf = self.planner_engine.run_method_comparison(
            task.molecule, ["HF", "B3LYP", "MP2"], task.basis,
            progress_callback=progress_callback,
        )
        return OrchestratorResult(
            plan=plan, workflow_result=wf, summary=wf.summary, success=wf.success
        )

    def _execute_basis_convergence(
        self,
        plan: WorkflowPlan,
        progress_callback: Optional[Callable] = None,
    ) -> OrchestratorResult:
        task = plan.tasks[0] if plan.tasks else None
        if not task:
            return OrchestratorResult(plan=plan, warnings=["No task in plan"])
        wf = self.planner_engine.run_basis_set_convergence(
            task.molecule, plan.method,
            ["sto-3g", "6-31g*", "cc-pvdz", "cc-pvtz"],
            progress_callback=progress_callback,
        )
        return OrchestratorResult(
            plan=plan, workflow_result=wf, summary=wf.summary, success=wf.success
        )
