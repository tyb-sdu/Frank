"""
异步智能体 — 支持非阻塞计算的 Frank 智能体。

核心能力：
1. 非阻塞执行计算
2. 实时进度反馈
3. 并行工作流
4. 支持取消
"""

import asyncio
from typing import Optional, Callable, AsyncIterator
from .agent import FrankAgent, ParsedIntent
from .executor import AsyncPySCFExecutor, AsyncTask, TaskStatus, AsyncStreamIterator
from .workflows import AsyncWorkflowEngine, AsyncWorkflowResult
from .core.parser import PySCFOutputParser
from .core.diagnostics import DiagnosticsEngine, format_diagnostics
from .core.interpreter import ResultInterpreter
from .molecules.database import get_molecule


class AsyncFrankAgent:
    """异步 Frank 智能体"""

    def __init__(
        self,
        work_dir: Optional[str] = None,
        timeout: int = 600,
        max_parallel: int = 4,
    ):
        """
        Parameters
        ----------
        work_dir : str, optional
            工作目录
        timeout : int
            计算超时时间（秒）
        max_parallel : int
            最大并行任务数
        """
        # 同步智能体（用于意图解析和代码生成）
        self._sync_agent = FrankAgent(work_dir=work_dir, timeout=timeout)

        # 异步执行器
        self.executor = AsyncPySCFExecutor(
            work_dir=work_dir,
            timeout=timeout,
            max_parallel=max_parallel,
        )

        # 异步工作流引擎
        self.workflow_engine = AsyncWorkflowEngine(
            executor=self.executor,
            timeout=timeout,
            max_parallel=max_parallel,
        )

        # 解析器和诊断器
        self.parser = PySCFOutputParser()
        self.diagnostics = DiagnosticsEngine()
        self.interpreter = ResultInterpreter()

    @property
    def sync_agent(self) -> FrankAgent:
        """获取同步智能体。"""
        return self._sync_agent

    def parse_intent(self, text: str) -> ParsedIntent:
        """解析意图（同步）。"""
        return self._sync_agent.parse_intent(text)

    def generate_code(self, intent: ParsedIntent):
        """生成代码（同步）。"""
        return self._sync_agent.generate_code(intent)

    async def run(
        self,
        text: str,
        interpret: bool = True,
        stream: bool = False,
    ) -> dict:
        """
        异步执行计算。

        Parameters
        ----------
        text : str
            用户输入
        interpret : bool
            是否解读结果
        stream : bool
            是否返回流式迭代器

        Returns
        -------
        dict
            计算结果
        """
        # 解析意图
        intent = self.parse_intent(text)

        # 生成代码
        code = None
        if intent.molecule:
            try:
                code = self.generate_code(intent)
            except Exception as e:
                intent.warnings.append(f"代码生成失败: {str(e)}")

        if not code:
            return {
                "intent": intent,
                "code": None,
                "script": "",
                "task": None,
                "parsed": {},
                "diagnostics": [],
                "interpretation": "",
                "warnings": intent.warnings,
            }

        # 组装脚本
        script = code.to_script()

        # 执行计算
        mol = get_molecule(intent.molecule)
        job_name = f"{mol.name}_{intent.method or 'b3lyp'}".lower()

        task = await self.executor.execute(script, job_name)

        # 解析结果
        parsed = {}
        if task.success:
            parsed = self.parser.parse_from_stdout(task.stdout)

        # 诊断
        diagnostics = []
        if task.error_type:
            diagnostics.extend(self.diagnostics.diagnose_scf_convergence(task.stdout))

        # 解读结果（使用统一入口）
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
            "task": task,
            "parsed": parsed,
            "diagnostics": diagnostics,
            "interpretation": interpretation,
            "warnings": intent.warnings,
        }

    async def run_with_streaming(
        self,
        text: str,
        on_output: Optional[Callable] = None,
    ) -> dict:
        """
        带实时输出的异步执行。

        Parameters
        ----------
        text : str
            用户输入
        on_output : Callable, optional
            输出回调函数

        Returns
        -------
        dict
            计算结果
        """
        # 解析意图
        intent = self.parse_intent(text)

        # 生成代码
        code = None
        if intent.molecule:
            try:
                code = self.generate_code(intent)
            except Exception as e:
                intent.warnings.append(f"代码生成失败: {str(e)}")

        if not code:
            return {
                "intent": intent,
                "code": None,
                "task": None,
            }

        # 组装脚本
        script = code.to_script()

        # 执行计算
        mol = get_molecule(intent.molecule)
        job_name = f"{mol.name}_{intent.method or 'b3lyp'}".lower()

        # 设置进度回调
        if on_output:
            async def progress_callback(task_id, message):
                on_output(message)
            self.executor.set_progress_callback(progress_callback)

        task = await self.executor.execute(script, job_name)

        # 解析结果
        parsed = {}
        if task.success:
            parsed = self.parser.parse_from_stdout(task.stdout)

        return {
            "intent": intent,
            "code": code,
            "task": task,
            "parsed": parsed,
        }

    async def get_stream_iterator(self, task_id: str) -> Optional[AsyncStreamIterator]:
        """
        获取任务的流式迭代器。

        Parameters
        ----------
        task_id : str
            任务 ID

        Returns
        -------
        AsyncStreamIterator, optional
            流式迭代器
        """
        task = self.executor.get_task(task_id)
        if not task:
            return None
        return AsyncStreamIterator(task)

    async def cancel(self, task_id: str) -> bool:
        """
        取消正在运行的任务。

        Parameters
        ----------
        task_id : str
            任务 ID

        Returns
        -------
        bool
            是否成功取消
        """
        return await self.executor.cancel(task_id)

    async def cancel_all(self):
        """取消所有正在运行的任务。"""
        await self.executor.cancel_all()

    def get_running_tasks(self) -> list[AsyncTask]:
        """获取正在运行的任务。"""
        return self.executor.get_running_tasks()

    def get_all_tasks(self) -> list[AsyncTask]:
        """获取所有任务。"""
        return self.executor.get_all_tasks()

    # ============================================================
    #  异步工作流
    # ============================================================

    async def run_method_comparison(
        self,
        molecule: str,
        methods: list[str],
        basis: str = "6-31g*",
    ) -> AsyncWorkflowResult:
        """
        并行方法对比。

        Parameters
        ----------
        molecule : str
            分子名称
        methods : list[str]
            方法列表
        basis : str
            基组
        """
        return await self.workflow_engine.run_method_comparison(
            molecule, methods, basis
        )

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
        return await self.workflow_engine.run_basis_convergence(
            molecule, method, basis_sets
        )

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
        return await self.workflow_engine.run_multi_molecule(
            molecules, method, basis
        )

    def get_help(self) -> str:
        """返回帮助信息。"""
        return self._sync_agent.get_help()
