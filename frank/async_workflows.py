"""
异步工作流引擎 — 支持并行执行的多步计算工作流。

核心能力：
1. 并行执行方法对比
2. 并行执行基组收敛测试
3. 实时进度反馈
4. 支持取消
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable
from .async_executor import AsyncPySCFExecutor, AsyncTask, TaskStatus
from .parser import PySCFOutputParser
from .diagnostics import DiagnosticsEngine, Diagnostic
from .templates.pyscf_templates import PySCFTemplateEngine
from .molecules import get_molecule


@dataclass
class AsyncWorkflowStep:
    """异步工作流步骤"""
    name: str
    description: str
    script: str = ""
    task: Optional[AsyncTask] = None
    parsed: dict = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    status: str = "pending"


@dataclass
class AsyncWorkflowResult:
    """异步工作流结果"""
    steps: list[AsyncWorkflowStep] = field(default_factory=list)
    success: bool = False
    summary: str = ""
    total_duration: float = 0.0

    @property
    def final_energy(self) -> Optional[float]:
        """获取最终能量。"""
        for step in reversed(self.steps):
            if step.parsed:
                if "scf" in step.parsed:
                    return step.parsed["scf"].energy
                if "mp2" in step.parsed:
                    return step.parsed["mp2"].mp2_total
                if "ccsd" in step.parsed:
                    return step.parsed["ccsd"].ccsd_t_total or step.parsed["ccsd"].ccsd_total
        return None


class AsyncWorkflowEngine:
    """异步工作流引擎"""

    def __init__(
        self,
        executor: Optional[AsyncPySCFExecutor] = None,
        timeout: int = 600,
        max_parallel: int = 4,
    ):
        self.executor = executor or AsyncPySCFExecutor(
            timeout=timeout,
            max_parallel=max_parallel,
        )
        self.parser = PySCFOutputParser()
        self.diagnostics = DiagnosticsEngine()
        self.template_engine = PySCFTemplateEngine()
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """设置进度回调。"""
        self._progress_callback = callback
        self.executor.set_progress_callback(callback)

    async def run_method_comparison(
        self,
        molecule: str,
        methods: list[str],
        basis: str = "6-31g*",
    ) -> AsyncWorkflowResult:
        """
        并行方法对比工作流。

        Parameters
        ----------
        molecule : str
            分子名称
        methods : list[str]
            方法列表
        basis : str
            基组
        """
        import time
        start_time = time.time()

        result = AsyncWorkflowResult()
        mol = get_molecule(molecule)

        # 生成所有脚本
        scripts = []
        for method in methods:
            step = AsyncWorkflowStep(
                name=f"calc_{method}",
                description=f"单点能计算 ({method}/{basis})",
            )
            result.steps.append(step)

            # 判断是 DFT 还是 HF
            is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]

            if is_dft:
                code = self.template_engine.generate_dft(molecule, method, basis)
            else:
                code = self.template_engine.generate_scf(molecule, method, basis)

            step.script = code.to_script()
            scripts.append((step.script, f"{mol.name}_{method}"))

        # 并行执行
        tasks = await self.executor.execute_parallel(scripts)

        # 处理结果
        for i, task in enumerate(tasks):
            step = result.steps[i]
            step.task = task

            if task.success:
                step.status = "success"
                step.parsed = self.parser.parse_from_stdout(task.stdout)
            else:
                step.status = "failed"

        # 汇总
        success_steps = [s for s in result.steps if s.status == "success"]
        result.success = len(success_steps) > 0
        result.total_duration = time.time() - start_time
        result.summary = self._generate_comparison_summary(
            result, mol.name_cn, methods, basis
        )

        return result

    async def run_basis_convergence(
        self,
        molecule: str,
        method: str = "B3LYP",
        basis_sets: list[str] = None,
    ) -> AsyncWorkflowResult:
        """
        并行基组收敛性测试。

        Parameters
        ----------
        molecule : str
            分子名称
        method : str
            计算方法
        basis_sets : list[str]
            基组列表
        """
        if basis_sets is None:
            basis_sets = ["6-31g*", "cc-pvdz", "cc-pvtz", "aug-cc-pvdz"]

        import time
        start_time = time.time()

        result = AsyncWorkflowResult()
        mol = get_molecule(molecule)

        # 生成所有脚本
        scripts = []
        for basis in basis_sets:
            step = AsyncWorkflowStep(
                name=f"basis_{basis}",
                description=f"单点能计算 ({method}/{basis})",
            )
            result.steps.append(step)

            code = self.template_engine.generate_dft(molecule, method, basis)
            step.script = code.to_script()
            scripts.append((step.script, f"{mol.name}_{basis}"))

        # 并行执行
        tasks = await self.executor.execute_parallel(scripts)

        # 处理结果
        for i, task in enumerate(tasks):
            step = result.steps[i]
            step.task = task

            if task.success:
                step.status = "success"
                step.parsed = self.parser.parse_from_stdout(task.stdout)
            else:
                step.status = "failed"

        # 汇总
        success_steps = [s for s in result.steps if s.status == "success"]
        result.success = len(success_steps) > 0
        result.total_duration = time.time() - start_time
        result.summary = self._generate_basis_convergence_summary(
            result, mol.name_cn, method, basis_sets
        )

        return result

    async def run_multi_molecule(
        self,
        molecules: list[str],
        method: str = "B3LYP",
        basis: str = "6-31g*",
    ) -> AsyncWorkflowResult:
        """
        并行计算多个分子。

        Parameters
        ----------
        molecules : list[str]
            分子列表
        method : str
            计算方法
        basis : str
            基组
        """
        import time
        start_time = time.time()

        result = AsyncWorkflowResult()

        # 生成所有脚本
        scripts = []
        for mol_name in molecules:
            mol = get_molecule(mol_name)
            step = AsyncWorkflowStep(
                name=f"calc_{mol.name}",
                description=f"计算 {mol.name_cn} ({method}/{basis})",
            )
            result.steps.append(step)

            is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]
            if is_dft:
                code = self.template_engine.generate_dft(mol_name, method, basis)
            else:
                code = self.template_engine.generate_scf(mol_name, method, basis)

            step.script = code.to_script()
            scripts.append((step.script, f"{mol.name}_{method}"))

        # 并行执行
        tasks = await self.executor.execute_parallel(scripts)

        # 处理结果
        for i, task in enumerate(tasks):
            step = result.steps[i]
            step.task = task

            if task.success:
                step.status = "success"
                step.parsed = self.parser.parse_from_stdout(task.stdout)
            else:
                step.status = "failed"

        # 汇总
        success_steps = [s for s in result.steps if s.status == "success"]
        result.success = len(success_steps) > 0
        result.total_duration = time.time() - start_time
        result.summary = self._generate_multi_molecule_summary(
            result, molecules, method, basis
        )

        return result

    def _generate_comparison_summary(
        self,
        result: AsyncWorkflowResult,
        mol_name: str,
        methods: list[str],
        basis: str,
    ) -> str:
        """生成方法对比总结。"""
        lines = [f"\n{'='*60}"]
        lines.append(f"  方法对比: {mol_name} (基组: {basis})")
        lines.append(f"{'='*60}")
        lines.append("")

        lines.append(f"{'方法':<15} {'能量 (Hartree)':<20} {'状态':<10}")
        lines.append(f"{'-'*45}")

        for step in result.steps:
            method = step.name.replace("calc_", "")
            if step.status == "success" and step.parsed:
                scf = step.parsed.get("scf")
                if scf and scf.energy:
                    lines.append(f"{method:<15} {scf.energy:<20.10f} [OK]")
                else:
                    lines.append(f"{method:<15} {'N/A':<20} [WARN]")
            else:
                lines.append(f"{method:<15} {'N/A':<20} [FAIL]")

        # 能量差
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

        lines.append(f"\n总耗时: {result.total_duration:.1f} 秒 (并行执行)")

        return "\n".join(lines)

    def _generate_basis_convergence_summary(
        self,
        result: AsyncWorkflowResult,
        mol_name: str,
        method: str,
        basis_sets: list[str],
    ) -> str:
        """生成基组收敛性总结。"""
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

            # 检查收敛
            if len(energies) >= 2:
                last_de = abs(energies[-1][1] - energies[-2][1]) * 627.509
                if last_de < 0.1:
                    lines.append(f"\n[OK] 基组已收敛 (最后两级差 < 0.1 kcal/mol)")
                else:
                    lines.append(f"\n[WARN] 基组可能未收敛 (最后两级差 = {last_de:.4f} kcal/mol)")

        lines.append(f"\n总耗时: {result.total_duration:.1f} 秒 (并行执行)")

        return "\n".join(lines)

    def _generate_multi_molecule_summary(
        self,
        result: AsyncWorkflowResult,
        molecules: list[str],
        method: str,
        basis: str,
    ) -> str:
        """生成多分子计算总结。"""
        lines = [f"\n{'='*60}"]
        lines.append(f"  多分子计算 ({method}/{basis})")
        lines.append(f"{'='*60}")
        lines.append("")

        lines.append(f"{'分子':<15} {'能量 (Hartree)':<20} {'状态':<10}")
        lines.append(f"{'-'*45}")

        for step in result.steps:
            mol_name = step.name.replace("calc_", "")
            if step.status == "success" and step.parsed:
                scf = step.parsed.get("scf")
                if scf and scf.energy:
                    lines.append(f"{mol_name:<15} {scf.energy:<20.10f} [OK]")
                else:
                    lines.append(f"{mol_name:<15} {'N/A':<20} [WARN]")
            else:
                lines.append(f"{mol_name:<15} {'N/A':<20} [FAIL]")

        lines.append(f"\n总耗时: {result.total_duration:.1f} 秒 (并行执行)")

        return "\n".join(lines)
