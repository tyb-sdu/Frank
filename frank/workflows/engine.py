from dataclasses import dataclass, field
from typing import Callable, Optional
from ..core.executor import PySCFExecutor, ExecutionResult
from ..core.parser import PySCFOutputParser
from ..core.diagnostics import DiagnosticsEngine, Diagnostic
from ..templates.pyscf_templates import PySCFTemplateEngine
from ..molecules.database import get_molecule


@dataclass
class WorkflowStep:
    name: str
    description: str
    script: str = ""
    result: Optional[ExecutionResult] = None
    parsed: dict = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    retry_log: list[str] = field(default_factory=list)
    status: str = "pending"


@dataclass
class WorkflowResult:
    steps: list[WorkflowStep] = field(default_factory=list)
    success: bool = False
    summary: str = ""

    @property
    def final_energy(self) -> Optional[float]:
        for step in reversed(self.steps):
            if step.parsed:
                if "scf" in step.parsed:
                    return step.parsed["scf"].energy
                if "mp2" in step.parsed:
                    return step.parsed["mp2"].mp2_total
                if "ccsd" in step.parsed:
                    return step.parsed["ccsd"].ccsd_t_total or step.parsed["ccsd"].ccsd_total
        return None


class WorkflowEngine:

    def __init__(self, executor: Optional[PySCFExecutor] = None):
        self.executor = executor or PySCFExecutor()
        self.parser = PySCFOutputParser()
        self.diagnostics = DiagnosticsEngine()
        self.template_engine = PySCFTemplateEngine()

    def run_geometry_optimization_frequency(
        self,
        molecule: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        solvent: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> WorkflowResult:
        result = WorkflowResult()
        mol = get_molecule(molecule)
        total_steps = 3 if basis.lower() in ["6-31g*", "6-31g(d)", "6-31g**", "6-31g(d,p)"] else 2

        step1 = WorkflowStep(
            name="geometry_optimization",
            description=f"Geometry optimization ({method}/{basis})",
        )
        result.steps.append(step1)

        if progress_callback:
            progress_callback("Geometry optimization", "running", 0, total_steps)

        code = self.template_engine.generate_geometry_opt(
            molecule, method, basis, solvent=solvent
        )
        step1.script = code.to_script()

        step1.status = "running"
        exec_result, retry_log = self.executor.execute_with_recovery(
            step1.script, f"{mol.name}_opt", original_basis=basis
        )
        step1.result = exec_result
        step1.retry_log = retry_log

        if exec_result.success:
            step1.status = "success"
            step1.parsed = self.parser.parse_from_stdout(exec_result.stdout)
            step1.diagnostics = self.diagnostics.diagnose_geometry_opt(
                converged=True, n_steps=100
            )
        else:
            step1.status = "failed"
            step1.diagnostics = [Diagnostic(
                level="error",
                category="workflow_step_failed",
                title="几何优化失败",
                description=exec_result.error_message or "未知错误",
                suggestions=["检查分子几何", "尝试不同的方法或基组"],
            )]
            result.summary = "几何优化失败，工作流终止。"
            return result

        step2 = WorkflowStep(
            name="frequency",
            description=f"Frequency calculation ({method}/{basis})",
        )
        result.steps.append(step2)

        if progress_callback:
            progress_callback("Frequency calculation", "running", 1, total_steps)

        freq_code = self.template_engine.generate_frequency(
            molecule, method, basis, solvent=solvent
        )
        step2.script = freq_code.to_script()

        step2.status = "running"
        freq_result, freq_retry_log = self.executor.execute_with_recovery(
            step2.script, f"{mol.name}_freq", original_basis=basis
        )
        step2.result = freq_result
        step2.retry_log = freq_retry_log

        if freq_result.success:
            step2.status = "success"
            step2.parsed = self.parser.parse_from_stdout(freq_result.stdout)
            freq_data = step2.parsed.get("frequency")
            if freq_data:
                step2.diagnostics = self.diagnostics.diagnose_frequency(
                    freq_data.n_imaginary, freq_data.imaginary_freqs
                )
        else:
            step2.status = "failed"
            step2.diagnostics = [Diagnostic(
                level="warning",
                category="frequency_failed",
                title="频率计算失败",
                description=freq_result.error_message or "未知错误",
                suggestions=["频率计算可能需要更多内存"],
            )]

        high_basis = basis
        if basis.lower() in ["6-31g*", "6-31g(d)", "6-31g**", "6-31g(d,p)"]:
            high_basis = "cc-pvtz"

        if high_basis != basis:
            step3 = WorkflowStep(
                name="single_point",
                description=f"High-accuracy single-point energy ({method}/{high_basis})",
            )
            result.steps.append(step3)

            if progress_callback:
                progress_callback("Single-point energy", "running", 2, total_steps)

            sp_code = self.template_engine.generate_dft(
                molecule, method, high_basis, solvent=solvent
            )
            step3.script = sp_code.to_script()

            step3.status = "running"
            sp_result, sp_retry_log = self.executor.execute_with_recovery(
                step3.script, f"{mol.name}_sp", original_basis=high_basis
            )
            step3.result = sp_result
            step3.retry_log = sp_retry_log

            if sp_result.success:
                step3.status = "success"
                step3.parsed = self.parser.parse_from_stdout(sp_result.stdout)
            else:
                step3.status = "failed"

        success_steps = [s for s in result.steps if s.status == "success"]
        result.success = len(success_steps) == len(result.steps)
        result.summary = self._generate_workflow_summary(result, mol.name_cn, method, basis)

        return result

    def run_method_comparison(
        self,
        molecule: str,
        methods: list[str],
        basis: str = "6-31g*",
        progress_callback: Optional[Callable] = None,
    ) -> WorkflowResult:
        result = WorkflowResult()
        mol = get_molecule(molecule)

        for i, method in enumerate(methods):
            step = WorkflowStep(
                name=f"calc_{method}",
                description=f"Single-point energy ({method}/{basis})",
            )
            result.steps.append(step)

            if progress_callback:
                progress_callback(f"Computing {method}", "running", i, len(methods))

            is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]

            if is_dft:
                code = self.template_engine.generate_dft(molecule, method, basis)
            else:
                code = self.template_engine.generate_scf(molecule, method, basis)

            step.script = code.to_script()

            step.status = "running"
            exec_result, retry_log = self.executor.execute_with_recovery(
                step.script, f"{mol.name}_{method}", original_basis=basis
            )
            step.result = exec_result
            step.retry_log = retry_log

            if exec_result.success:
                step.status = "success"
                step.parsed = self.parser.parse_from_stdout(exec_result.stdout)
            else:
                step.status = "failed"

        success_steps = [s for s in result.steps if s.status == "success"]
        result.success = len(success_steps) > 0
        result.summary = self._generate_comparison_summary(result, mol.name_cn, methods, basis)

        return result

    def run_basis_set_convergence(
        self,
        molecule: str,
        method: str = "B3LYP",
        basis_sets: list[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> WorkflowResult:
        if basis_sets is None:
            basis_sets = ["6-31g*", "cc-pvdz", "cc-pvtz", "aug-cc-pvdz"]

        result = WorkflowResult()
        mol = get_molecule(molecule)

        for i, basis in enumerate(basis_sets):
            step = WorkflowStep(
                name=f"basis_{basis}",
                description=f"Single-point energy ({method}/{basis})",
            )
            result.steps.append(step)

            if progress_callback:
                progress_callback(f"Basis: {basis}", "running", i, len(basis_sets))

            code = self.template_engine.generate_dft(molecule, method, basis)
            step.script = code.to_script()

            step.status = "running"
            exec_result, retry_log = self.executor.execute_with_recovery(
                step.script, f"{mol.name}_{basis}", original_basis=basis
            )
            step.result = exec_result
            step.retry_log = retry_log

            if exec_result.success:
                step.status = "success"
                step.parsed = self.parser.parse_from_stdout(exec_result.stdout)
            else:
                step.status = "failed"

        success_steps = [s for s in result.steps if s.status == "success"]
        result.success = len(success_steps) > 0
        result.summary = self._generate_basis_convergence_summary(
            result, mol.name_cn, method, basis_sets
        )

        return result

    def _generate_workflow_summary(
        self,
        result: WorkflowResult,
        mol_name: str,
        method: str,
        basis: str,
    ) -> str:
        lines = [f"\n{'='*60}"]
        lines.append(f"  工作流总结: {mol_name} ({method}/{basis})")
        lines.append(f"{'='*60}")
        lines.append("")

        for step in result.steps:
            status_icon = "[OK]" if step.status == "success" else "[FAIL]"
            lines.append(f"{status_icon} {step.description}")

            if step.parsed:
                if "scf" in step.parsed:
                    lines.append(f"   能量: {step.parsed['scf'].energy:.10f} Hartree")
                if "frequency" in step.parsed:
                    freq = step.parsed["frequency"]
                    if freq.is_minimum:
                        lines.append(f"   频率: 无虚频 [OK]")
                    else:
                        lines.append(f"   频率: {freq.n_imaginary} 个虚频 [WARN]")

        final_e = result.final_energy
        if final_e:
            lines.append(f"\n最终能量: {final_e:.10f} Hartree")
            lines.append(f"           = {final_e * 27.2114:.6f} eV")
            lines.append(f"           = {final_e * 627.509:.4f} kcal/mol")

        return "\n".join(lines)

    def _generate_comparison_summary(
        self,
        result: WorkflowResult,
        mol_name: str,
        methods: list[str],
        basis: str,
    ) -> str:
        lines = [f"\n{'='*60}"]
        lines.append(f"  方法对比: {mol_name} (基组: {basis})")
        lines.append(f"{'='*60}")
        lines.append("")

        lines.append(f"{'方法':<15} {'能量 (Hartree)':<20} {'状态':<10}")
        lines.append(f"{'-'*45}")

        for step in result.steps:
            method = step.name.replace("calc_", "")
            if step.status == "success" and step.parsed:
                energy = step.parsed.get("scf", None)
                if energy and energy.energy:
                    lines.append(f"{method:<15} {energy.energy:<20.10f} [OK]")
                else:
                    lines.append(f"{method:<15} {'N/A':<20} [WARN]")
            else:
                lines.append(f"{method:<15} {'N/A':<20} [FAIL]")

        energies = []
        for step in result.steps:
            if step.status == "success" and step.parsed:
                scf = step.parsed.get("scf")
                if scf and scf.energy:
                    energies.append((step.name.replace("calc_", ""), scf.energy))

        if len(energies) >= 2:
            lines.append(f"\n能量差:")
            for i in range(len(energies)):
                for j in range(i+1, len(energies)):
                    de = (energies[j][1] - energies[i][1]) * 627.509
                    lines.append(f"  {energies[j][0]} - {energies[i][0]} = {de:.4f} kcal/mol")

        return "\n".join(lines)

    def _generate_basis_convergence_summary(
        self,
        result: WorkflowResult,
        mol_name: str,
        method: str,
        basis_sets: list[str],
    ) -> str:
        lines = [f"\n{'='*60}"]
        lines.append(f"  基组收敛性: {mol_name} ({method})")
        lines.append(f"{'='*60}")
        lines.append("")

        lines.append(f"{'基组':<15} {'能量 (Hartree)':<20} {'ΔE (kcal/mol)':<15} {'状态':<10}")
        lines.append(f"{'-'*60}")

        energies = []
        for step in result.steps:
            basis = step.name.replace("basis_", "")
            if step.status == "success" and step.parsed:
                scf = step.parsed.get("scf")
                if scf and scf.energy:
                    energies.append((basis, scf.energy))

        if energies:
            ref_energy = energies[0][1]
            for basis, energy in energies:
                de = (energy - ref_energy) * 627.509
                lines.append(f"{basis:<15} {energy:<20.10f} {de:<15.4f} [OK]")

            if len(energies) >= 2:
                last_de = abs(energies[-1][1] - energies[-2][1]) * 627.509
                if last_de < 0.1:
                    lines.append(f"\n[OK] 基组已收敛 (最后两级差 < 0.1 kcal/mol)")
                else:
                    lines.append(f"\n[WARN] 基组可能未收敛 (最后两级差 = {last_de:.4f} kcal/mol)")

        return "\n".join(lines)

    def run_pes_scan(
        self,
        molecule: str,
        scan_type: str = "bond",
        atom_indices: tuple[int, int] = (0, 1),
        method: str = "B3LYP",
        basis: str = "6-31g*",
        n_points: int = 11,
        range_start: float = 0.8,
        range_end: float = 2.0,
        progress_callback: Optional[Callable] = None,
    ) -> WorkflowResult:
        result = WorkflowResult()
        mol = get_molecule(molecule)

        import numpy as np
        scan_values = np.linspace(range_start, range_end, n_points)

        for i, value in enumerate(scan_values):
            step = WorkflowStep(
                name=f"scan_{i}",
                description=f"Scan point {i+1}/{n_points}: {scan_type}={value:.3f}",
            )
            result.steps.append(step)

            if progress_callback:
                progress_callback(f"PES scan: {scan_type}={value:.3f}", "running", i, n_points)

            script = self._generate_scan_script(
                molecule, method, basis, scan_type, atom_indices, value
            )
            step.script = script

            step.status = "running"
            exec_result, retry_log = self.executor.execute_with_recovery(
                script, f"{mol.name}_scan{i}", original_basis=basis
            )
            step.result = exec_result
            step.retry_log = retry_log

            if exec_result.success:
                step.status = "success"
                step.parsed = self.parser.parse_from_stdout(exec_result.stdout)
            else:
                step.status = "failed"

        success_steps = [s for s in result.steps if s.status == "success"]
        result.success = len(success_steps) > 0
        result.summary = self._generate_pes_summary(
            result, mol.name_cn, scan_type, scan_values.tolist()
        )

        return result

    def _generate_scan_script(
        self,
        molecule: str,
        method: str,
        basis: str,
        scan_type: str,
        atom_indices: tuple[int, int],
        value: float,
    ) -> str:
        mol = get_molecule(molecule)
        from ..molecules.database import get_pyscf_geometry
        geometry = get_pyscf_geometry(mol)

        is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]
        from ..methods.scf import choose_scf_type
        scf_type = choose_scf_type(mol.spin)

        a1, a2 = atom_indices
        lines = [
            "from pyscf import gto, scf, dft",
            "import numpy as np",
            "",
            f"mol = gto.Mole()",
            f"mol.atom = '''",
            f"{geometry}",
            f"'''",
            f"mol.basis = '{basis}'",
            f"mol.verbose = 0",
            f"mol.build()",
            "",
            f"# 修改几何: {scan_type} = {value:.4f}",
        ]

        if scan_type == "bond":
            lines.extend([
                f"coords = mol.atom_coords()",
                f"vec = coords[{a2}] - coords[{a1}]",
                f"vec = vec / np.linalg.norm(vec)",
                f"new_pos = coords[{a1}] + vec * {value:.6f} / 0.529177",
                f"mol.atom[{a2}] = (mol.atom[{a2}][0], new_pos.tolist())",
                f"mol.build()",
            ])
        elif scan_type == "angle":
            lines.append(f"# 键角扫描: 需要设置三个原子索引")
            lines.append(f"# 当前仅支持 bond 和 dihedral 扫描")
        elif scan_type == "dihedral":
            lines.append(f"# 二面角扫描: 需要设置四个原子索引")
            lines.append(f"# 当前仅支持 bond 扫描")

        if is_dft:
            scf_class = "UKS" if mol.spin > 0 else "RKS"
            lines.extend([
                "",
                f"mf = dft.{scf_class}(mol)",
                f"mf.xc = '{method}'",
                f"mf.kernel()",
                f"print(f'Energy: {{mf.e_tot:.10f}} Hartree')",
            ])
        else:
            lines.extend([
                "",
                f"mf = scf.{scf_type}(mol)",
                f"mf.kernel()",
                f"print(f'Energy: {{mf.e_tot:.10f}} Hartree')",
            ])

        return "\n".join(lines)

    def _generate_pes_summary(
        self,
        result: WorkflowResult,
        mol_name: str,
        scan_type: str,
        scan_values: list[float],
    ) -> str:
        lines = [f"\n{'='*60}"]
        lines.append(f"  势能面扫描: {mol_name} ({scan_type})")
        lines.append(f"{'='*60}\n")

        energies = []
        for step in result.steps:
            if step.status == "success" and step.parsed:
                scf = step.parsed.get("scf")
                if scf and scf.energy:
                    energies.append(scf.energy)
                else:
                    energies.append(None)
            else:
                energies.append(None)

        valid_e = [(i, e) for i, e in enumerate(energies) if e is not None]
        if valid_e:
            min_idx, min_e = min(valid_e, key=lambda x: x[1])

            lines.append(f"{'扫描值':<12} {'能量 (Hartree)':<20} {'ΔE (kcal/mol)':<15} {'状态'}")
            lines.append(f"{'-'*55}")

            for i, (val, e) in enumerate(zip(scan_values, energies)):
                if e is not None:
                    de = (e - min_e) * 627.509
                    marker = " ← 最低" if i == min_idx else ""
                    lines.append(f"{val:<12.4f} {e:<20.10f} {de:<15.4f} [OK]{marker}")
                else:
                    lines.append(f"{val:<12.4f} {'N/A':<20} {'N/A':<15} [FAIL]")

            lines.append(f"\n最低能量点: {scan_values[min_idx]:.4f}, E = {min_e:.10f} Hartree")

        return "\n".join(lines)

    def run_solvation_free_energy(
        self,
        molecule: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        solvent: str = "water",
        progress_callback: Optional[Callable] = None,
    ) -> WorkflowResult:
        from ..methods.solvation import get_solvent

        result = WorkflowResult()
        mol = get_molecule(molecule)
        solvent_info = get_solvent(solvent)

        step1 = WorkflowStep(name="gas_opt", description=f"Gas-phase geometry optimization ({method}/{basis})")
        result.steps.append(step1)
        if progress_callback:
            progress_callback("Gas-phase optimization", "running", 0, 3)
        code = self.template_engine.generate_geometry_opt(molecule, method, basis)
        step1.script = code.to_script()
        step1.status = "running"
        exec_result, retry_log = self.executor.execute_with_recovery(
            step1.script, f"{mol.name}_gas_opt", original_basis=basis
        )
        step1.result = exec_result
        step1.retry_log = retry_log
        if exec_result.success:
            step1.status = "success"
            step1.parsed = self.parser.parse_from_stdout(exec_result.stdout)
        else:
            step1.status = "failed"
            result.summary = "Gas-phase optimization failed; workflow terminated."
            return result

        step2 = WorkflowStep(name="gas_freq", description=f"Gas-phase frequency calculation ({method}/{basis})")
        result.steps.append(step2)
        if progress_callback:
            progress_callback("Gas-phase frequency", "running", 1, 3)
        freq_code = self.template_engine.generate_frequency(molecule, method, basis)
        step2.script = freq_code.to_script()
        step2.status = "running"
        freq_result, freq_retry = self.executor.execute_with_recovery(
            step2.script, f"{mol.name}_gas_freq", original_basis=basis
        )
        step2.result = freq_result
        step2.retry_log = freq_retry
        if freq_result.success:
            step2.status = "success"
            step2.parsed = self.parser.parse_from_stdout(freq_result.stdout)
        else:
            step2.status = "failed"

        step3 = WorkflowStep(
            name="liquid_sp",
            description=f"Solution-phase single point ({method}/{basis}, solvent: {solvent_info.name_cn})",
        )
        result.steps.append(step3)
        if progress_callback:
            progress_callback("Solution-phase calculation", "running", 2, 3)
        solv_code = self.template_engine.generate_solvation(
            molecule, method, basis, solvent=solvent
        )
        step3.script = solv_code.to_script()
        step3.status = "running"
        solv_result, solv_retry = self.executor.execute_with_recovery(
            step3.script, f"{mol.name}_solv", original_basis=basis
        )
        step3.result = solv_result
        step3.retry_log = solv_retry
        if solv_result.success:
            step3.status = "success"
            step3.parsed = self.parser.parse_from_stdout(solv_result.stdout)
        else:
            step3.status = "failed"

        success_steps = [s for s in result.steps if s.status == "success"]
        result.success = len(success_steps) >= 2

        gas_e = step1.parsed.get("scf", None) if step1.parsed else None
        solv_e = step3.parsed.get("scf", None) if step3.parsed else None

        if gas_e and gas_e.energy and solv_e and solv_e.energy:
            dg_solv = (solv_e.energy - gas_e.energy) * 627.509
            lines = [f"\n{'='*60}"]
            lines.append(f"  溶剂化自由能: {mol.name_cn} in {solvent_info.name_cn}")
            lines.append(f"{'='*60}\n")
            lines.append(f"气相能量:   {gas_e.energy:.10f} Hartree")
            lines.append(f"液相能量:   {solv_e.energy:.10f} Hartree")
            lines.append(f"ΔG_solv:   {dg_solv:+.4f} kcal/mol")
            if dg_solv < -5:
                lines.append(f"提示: 溶剂化能较大，分子在 {solvent_info.name_cn} 中溶解性好")
            result.summary = "\n".join(lines)
        else:
            result.summary = "溶剂化计算完成（部分步骤失败，无法计算 ΔG_solv）"

        return result
