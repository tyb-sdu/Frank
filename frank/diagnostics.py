from dataclasses import dataclass
from typing import Optional


@dataclass
class Diagnostic:
    level: str
    category: str
    title: str
    description: str
    suggestions: list[str]
    auto_fix: Optional[str] = None


class DiagnosticsEngine:

    def diagnose_scf_convergence(
        self,
        output: str,
        n_cycles: int = 0,
        max_cycle: int = 50,
    ) -> list[Diagnostic]:
        diagnostics = []

        if n_cycles >= max_cycle:
            diag = Diagnostic(
                level="error",
                category="scf_convergence",
                title="SCF 未收敛",
                description=f"SCF 在 {max_cycle} 次迭代后未收敛。",
                suggestions=[
                    "增加最大迭代次数: mf.max_cycle = 200",
                    "使用阻尼 DIIS: mf.diis_space = 8",
                    "尝试不同的初始猜测: mf.init_guess = 'minao'",
                    "对于开壳层体系，尝试 UHF 而非 RHF",
                    "检查分子几何是否合理",
                ],
                auto_fix="mf.max_cycle = 200\nmf.diis_space = 8",
            )
            diagnostics.append(diag)

        if "oscillat" in output.lower() or "diis error" in output.lower():
            diag = Diagnostic(
                level="warning",
                category="scf_oscillation",
                title="SCF 振荡",
                description="SCF 能量在迭代中振荡，可能需要阻尼。",
                suggestions=[
                    "使用阻尼: mf.damp = 0.5",
                    "增加 DIIS 空间: mf.diis_space = 10",
                    "尝试 level shift: mf.level_shift = 0.2",
                ],
                auto_fix="mf.damp = 0.5\nmf.level_shift = 0.2",
            )
            diagnostics.append(diag)

        return diagnostics

    def diagnose_basis(
        self,
        elements: list[str],
        basis: str,
        method: str,
    ) -> list[Diagnostic]:
        diagnostics = []

        post_hf_methods = ["mp2", "ccsd", "ccsd(t)", "casscf"]
        is_post_hf = any(m in method.lower() for m in post_hf_methods)

        if is_post_hf:
            split_valence = ["6-31g", "6-311g", "3-21g"]
            is_split_valence = any(basis.lower().startswith(sv) for sv in split_valence)

            if is_split_valence:
                diag = Diagnostic(
                    level="warning",
                    category="basis_method_mismatch",
                    title="基组-方法不匹配",
                    description=f"后 HF 方法 ({method}) 通常需要相关一致基组。",
                    suggestions=[
                        "推荐使用 cc-pVDZ 或 cc-pVTZ",
                        "如果需要弥散函数，使用 aug-cc-pVDZ",
                        "使用 def2-TZVP 也可以",
                    ],
                    auto_fix="basis = 'cc-pvdz'",
                )
                diagnostics.append(diag)

        if "阴离子" in str(elements) or any(e in ["F", "Cl", "O"] for e in elements):
            if "+" not in basis and "aug" not in basis.lower():
                diag = Diagnostic(
                    level="info",
                    category="basis_diffuse",
                    title="考虑弥散函数",
                    description="对于阴离子或电负性原子，弥散函数可能很重要。",
                    suggestions=[
                        "使用 6-31+G* 添加弥散函数",
                        "使用 aug-cc-pVDZ 添加弥散函数",
                    ],
                )
                diagnostics.append(diag)

        return diagnostics

    def diagnose_frequency(
        self,
        n_imaginary: int,
        imaginary_freqs: list[float],
    ) -> list[Diagnostic]:
        diagnostics = []

        if n_imaginary == 0:
            diag = Diagnostic(
                level="info",
                category="frequency_minimum",
                title="极小值点确认",
                description="没有虚频，结构为极小值点（可能是局部极小）。",
                suggestions=[
                    "可以进行更高精度的单点能计算",
                    "考虑使用更大的基组",
                ],
            )
            diagnostics.append(diag)

        elif n_imaginary == 1:
            if imaginary_freqs and abs(imaginary_freqs[0]) > 100:
                diag = Diagnostic(
                    level="warning",
                    category="frequency_transition_state",
                    title="可能为过渡态",
                    description=f"有 1 个虚频 ({imaginary_freqs[0]:.1f} cm^-1)，可能是过渡态。",
                    suggestions=[
                        "检查虚频对应的振动模式是否为反应坐标",
                        "如果期望是极小值，需要重新优化几何",
                        "尝试使用更严格的收敛标准",
                        "沿虚频方向扰动几何后重新优化",
                    ],
                )
                diagnostics.append(diag)
            else:
                diag = Diagnostic(
                    level="warning",
                    category="frequency_small_imaginary",
                    title="小虚频",
                    description=f"有 1 个很小的虚频 ({imaginary_freqs[0]:.1f} cm^-1)，可能是数值噪声。",
                    suggestions=[
                        "可以忽略小于 50 cm^-1 的虚频",
                        "使用更严格的积分精度: mol.precision = 1e-10",
                    ],
                )
                diagnostics.append(diag)

        else:
            diag = Diagnostic(
                level="error",
                category="frequency_multiple_imaginary",
                title="多个虚频",
                description=f"有 {n_imaginary} 个虚频，结构不是极小值点。",
                suggestions=[
                    "需要重新优化几何结构",
                    "检查初始几何是否合理",
                    "尝试使用不同的优化算法",
                    "增加优化步数",
                ],
            )
            diagnostics.append(diag)

        return diagnostics

    def diagnose_geometry_opt(
        self,
        converged: bool,
        n_steps: int,
        max_steps: int = 100,
    ) -> list[Diagnostic]:
        diagnostics = []

        if not converged:
            if n_steps >= max_steps:
                diag = Diagnostic(
                    level="error",
                    category="geomopt_not_converged",
                    title="几何优化未收敛",
                    description=f"在 {max_steps} 步内未收敛。",
                    suggestions=[
                        "增加最大步数: maxsteps=200",
                        "使用更严格的初始几何",
                        "尝试使用不同的优化器",
                        "检查分子是否合理",
                    ],
                    auto_fix="maxsteps=200",
                )
                diagnostics.append(diag)
            else:
                diag = Diagnostic(
                    level="warning",
                    category="geomopt_convergence_issue",
                    title="几何优化收敛问题",
                    description="优化过程可能有问题。",
                    suggestions=[
                        "检查每一步的能量变化",
                        "确认梯度是否在减小",
                    ],
                )
                diagnostics.append(diag)

        return diagnostics

    def diagnose_memory(
        self,
        n_basis: int,
        method: str,
    ) -> list[Diagnostic]:
        diagnostics = []

        eri_memory_gb = (n_basis ** 4 * 8) / (1024 ** 3)

        if eri_memory_gb > 8:
            diag = Diagnostic(
                level="warning",
                category="memory_high",
                title="内存需求较高",
                description=f"估计需要 {eri_memory_gb:.1f} GB 内存存储双电子积分。",
                suggestions=[
                    "使用密度拟合 (DF) 加速: mf = mf.density_fit()",
                    "使用积分直接计算: mol.direct_scf = True",
                    "考虑使用更小的基组",
                ],
                auto_fix="mf = mf.density_fit()",
            )
            diagnostics.append(diag)

        if "ccsd" in method.lower():
            memory_gb = (n_basis ** 6 * 8) / (1024 ** 3)
            if memory_gb > 1:
                diag = Diagnostic(
                    level="warning",
                    category="ccsd_memory",
                    title="CCSD 内存需求",
                    description=f"CCSD 计算估计需要 {memory_gb:.1f} GB 内存（N^6 标度）。",
                    suggestions=[
                        "使用 DF-CCSD 加速",
                        "考虑使用 DMRG-CCSD 对于大体系",
                        "使用冻结核心近似减少计算量",
                    ],
                )
                diagnostics.append(diag)

        return diagnostics

    def diagnose_all(
        self,
        output: str,
        elements: list[str],
        basis: str,
        method: str,
        n_imaginary: int = 0,
        imaginary_freqs: list[float] = None,
        converged: bool = True,
        n_steps: int = 0,
        n_basis: int = 0,
    ) -> list[Diagnostic]:
        all_diagnostics = []

        all_diagnostics.extend(
            self.diagnose_scf_convergence(output)
        )

        all_diagnostics.extend(
            self.diagnose_basis(elements, basis, method)
        )

        if imaginary_freqs:
            all_diagnostics.extend(
                self.diagnose_frequency(n_imaginary, imaginary_freqs)
            )

        if n_steps > 0:
            all_diagnostics.extend(
                self.diagnose_geometry_opt(converged, n_steps)
            )

        if n_basis > 0:
            all_diagnostics.extend(
                self.diagnose_memory(n_basis, method)
            )

        return all_diagnostics


def format_diagnostics(diagnostics: list[Diagnostic]) -> str:
    if not diagnostics:
        return "[OK] 未发现明显问题"

    lines = []
    level_icons = {
        "info": "[INFO] ",
        "warning": "[WARN] ",
        "error": "[FAIL]",
        "critical": "[CRITICAL]",
    }

    for diag in diagnostics:
        icon = level_icons.get(diag.level, "[?]")
        lines.append(f"\n{icon} [{diag.category}] {diag.title}")
        lines.append(f"   {diag.description}")
        if diag.suggestions:
            lines.append("   建议:")
            for i, s in enumerate(diag.suggestions, 1):
                lines.append(f"     {i}. {s}")
        if diag.auto_fix:
            lines.append(f"   自动修复代码:")
            lines.append(f"     {diag.auto_fix}")

    return "\n".join(lines)
