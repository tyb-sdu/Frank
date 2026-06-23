"""Self-correction engine — Aitomia-inspired automatic error recovery in workflows.

Detects imaginary frequencies after geometry optimization and triggers re-optimization.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..core.diagnostics import Diagnostic, DiagnosticsEngine
from ..core.executor import PySCFExecutor, ExecutionResult
from ..core.parser import PySCFOutputParser
from ..templates.pyscf_templates import PySCFTemplateEngine


@dataclass
class CorrectionAttempt:
    strategy: str
    description: str
    success: bool = False
    n_imaginary_before: int = 0
    n_imaginary_after: int = 0


@dataclass
class SelfCorrectionResult:
    molecule: str
    opt_result: Optional[ExecutionResult] = None
    freq_result: Optional[ExecutionResult] = None
    opt_parsed: dict = field(default_factory=dict)
    freq_parsed: dict = field(default_factory=dict)
    attempts: list[CorrectionAttempt] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    success: bool = False
    is_minimum: bool = False

    @property
    def n_imaginary(self) -> int:
        freq = self.freq_parsed.get("frequency")
        return freq.n_imaginary if freq else 0


CORRECTION_STRATEGIES = [
    ("tighten_convergence", "Tighten SCF/geometry convergence criteria"),
    ("reoptimize", "Re-run geometry optimization from current structure"),
]


class SelfCorrectionEngine:
    """Run opt→freq with automatic self-correction on imaginary frequencies."""

    MAX_RETRIES = 2

    def __init__(self, executor: Optional[PySCFExecutor] = None):
        self.executor = executor or PySCFExecutor()
        self.parser = PySCFOutputParser()
        self.diagnostics = DiagnosticsEngine()
        self.templates = PySCFTemplateEngine()

    def run_opt_freq_with_correction(
        self,
        molecule: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        progress_callback: Optional[Callable] = None,
    ) -> SelfCorrectionResult:
        result = SelfCorrectionResult(molecule=molecule)

        # Step 1: Geometry optimization
        if progress_callback:
            progress_callback(f"Optimizing {molecule}", "running")

        opt_code = self.templates.generate_geometry_opt(molecule, method, basis)
        opt_script = opt_code.to_script()
        opt_exec, _ = self.executor.execute_with_recovery(
            opt_script, f"{molecule}_opt_sc", original_basis=basis
        )
        result.opt_result = opt_exec

        if not opt_exec.success:
            result.diagnostics.append(Diagnostic(
                level="error",
                category="opt_failed",
                title="Geometry optimization failed",
                description=opt_exec.error_message or "Unknown error",
                suggestions=["Check initial geometry", "Try a different method or basis set"],
            ))
            return result

        result.opt_parsed = self.parser.parse_from_stdout(opt_exec.stdout)

        # Step 2: Frequency with self-correction loop
        retries = 0
        while retries <= self.MAX_RETRIES:
            if progress_callback:
                progress_callback(f"Frequency: {molecule} (attempt {retries + 1})", "running")

            freq_code = self.templates.generate_frequency(molecule, method, basis)
            freq_script = freq_code.to_script()

            if retries > 0:
                freq_script = self._inject_tight_convergence(freq_script)

            freq_exec, _ = self.executor.execute_with_recovery(
                freq_script, f"{molecule}_freq_sc{retries}", original_basis=basis
            )
            result.freq_result = freq_exec

            if not freq_exec.success:
                result.diagnostics.append(Diagnostic(
                    level="error",
                    category="freq_failed",
                    title="Frequency calculation failed",
                    description=freq_exec.error_message or "Unknown error",
                    suggestions=["Check if optimization converged to a minimum"],
                ))
                return result

            result.freq_parsed = self.parser.parse_from_stdout(freq_exec.stdout)
            freq_data = result.freq_parsed.get("frequency")
            n_imag = freq_data.n_imaginary if freq_data else 0

            attempt = CorrectionAttempt(
                strategy=CORRECTION_STRATEGIES[min(retries, 1)][0],
                description=CORRECTION_STRATEGIES[min(retries, 1)][1],
                n_imaginary_before=n_imag,
            )

            if n_imag == 0:
                attempt.success = True
                attempt.n_imaginary_after = 0
                result.attempts.append(attempt)
                result.success = True
                result.is_minimum = True
                result.diagnostics.extend(
                    self.diagnostics.diagnose_frequency(0, [])
                )
                return result

            # Small imaginary frequency (< 50 cm⁻¹) — likely numerical noise
            if n_imag == 1 and freq_data.imaginary_freqs:
                if abs(freq_data.imaginary_freqs[0]) < 50:
                    attempt.success = True
                    attempt.n_imaginary_after = n_imag
                    result.attempts.append(attempt)
                    result.success = True
                    result.is_minimum = True
                    result.diagnostics.extend(
                        self.diagnostics.diagnose_frequency(n_imag, freq_data.imaginary_freqs)
                    )
                    return result

            attempt.n_imaginary_after = n_imag
            result.attempts.append(attempt)

            if retries < self.MAX_RETRIES:
                # Self-correction: re-optimize
                if progress_callback:
                    progress_callback(
                        f"Self-correction: re-optimizing {molecule} ({n_imag} imaginary freq)",
                        "correction",
                    )
                opt_code = self.templates.generate_geometry_opt(molecule, method, basis)
                opt_script = self._inject_tight_convergence(opt_code.to_script())
                opt_exec, _ = self.executor.execute_with_recovery(
                    opt_script, f"{molecule}_opt_sc_retry{retries}", original_basis=basis
                )
                if not opt_exec.success:
                    break
                result.opt_result = opt_exec
                result.opt_parsed = self.parser.parse_from_stdout(opt_exec.stdout)

            retries += 1

        freq_data = result.freq_parsed.get("frequency")
        n_imag = freq_data.n_imaginary if freq_data else -1
        result.diagnostics.extend(
            self.diagnostics.diagnose_frequency(
                n_imag, freq_data.imaginary_freqs if freq_data else []
            )
        )
        result.diagnostics.append(Diagnostic(
            level="warning",
            category="self_correction_exhausted",
            title="Self-correction exhausted",
            description=f"Still {n_imag} imaginary frequency(ies) after {self.MAX_RETRIES} retries.",
            suggestions=[
                "Verify the initial structure",
                "Try a different initial guess or conformer",
                "Use tighter convergence: mol.conv_tol = 1e-9",
            ],
        ))
        result.success = freq_data is not None
        result.is_minimum = n_imag == 0
        return result

    def _inject_tight_convergence(self, script: str) -> str:
        """Inject tighter convergence settings into a PySCF script."""
        patch = "mol.conv_tol = 1e-9\nmf.conv_tol = 1e-9\nmf.max_cycle = 200"
        lines = script.split("\n")
        insert_idx = None
        for i, line in enumerate(lines):
            if "mf.kernel()" in line or "mf.run()" in line:
                insert_idx = i
                break
        if insert_idx is not None:
            lines.insert(insert_idx, patch)
        else:
            lines.append(patch)
        return "\n".join(lines)
