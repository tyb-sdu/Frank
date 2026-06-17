"""
异步执行引擎 — 基于 asyncio.subprocess 的非阻塞计算执行器。

核心能力：
1. 非阻塞执行 PySCF 代码
2. 实时流式输出（进度反馈）
3. 支持取消正在运行的计算
4. 并行执行多个计算任务
"""

import os
import sys
import json
import time
import asyncio
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, AsyncIterator
from enum import Enum
from .executor_common import enhance_script, classify_error


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTask:
    """异步计算任务"""
    task_id: str
    name: str
    script: str
    status: TaskStatus = TaskStatus.PENDING
    process: Optional[asyncio.subprocess.Process] = None
    stdout_lines: list[str] = field(default_factory=list)
    stderr_lines: list[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    return_code: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    output_dir: str = ""

    @property
    def duration(self) -> float:
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    @property
    def stdout(self) -> str:
        return "\n".join(self.stdout_lines)

    @property
    def stderr(self) -> str:
        return "\n".join(self.stderr_lines)

    @property
    def success(self) -> bool:
        return self.status == TaskStatus.COMPLETED and self.return_code == 0


class AsyncPySCFExecutor:
    """异步 PySCF 执行器"""

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
            单个任务超时时间（秒）
        max_parallel : int
            最大并行任务数
        """
        self.work_dir = work_dir
        self.timeout = timeout
        self.max_parallel = max_parallel
        self._tasks: dict[str, AsyncTask] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数。"""
        self._progress_callback = callback

    async def _emit_progress(self, task_id: str, message: str):
        """发送进度更新。"""
        if self._progress_callback:
            await self._progress_callback(task_id, message)

    async def execute(
        self,
        script: str,
        job_name: str = "frank_job",
        task_id: Optional[str] = None,
    ) -> AsyncTask:
        """
        异步执行 PySCF 脚本。

        Parameters
        ----------
        script : str
            Python 脚本内容
        job_name : str
            作业名称
        task_id : str, optional
            任务 ID（自动生成）

        Returns
        -------
        AsyncTask
            异步任务对象
        """
        if task_id is None:
            task_id = f"{job_name}_{int(time.time()*1000)}"

        # 创建任务
        task = AsyncTask(
            task_id=task_id,
            name=job_name,
            script=script,
        )
        self._tasks[task_id] = task

        # 创建工作目录
        if self.work_dir:
            work_dir = Path(self.work_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
        else:
            work_dir = Path(tempfile.mkdtemp(prefix="frank_async_"))

        task.output_dir = str(work_dir)

        # 写入脚本
        script_file = work_dir / f"{job_name}.py"
        enhanced_script = self._enhance_script(script)
        script_file.write_text(enhanced_script, encoding="utf-8")

        # 初始化信号量
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_parallel)

        # 执行
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()

        try:
            async with self._semaphore:
                await self._run_process(task, script_file, work_dir)
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.end_time = time.time()
            if task.process:
                task.process.terminate()
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_type = "executor_error"
            task.error_message = str(e)
            task.end_time = time.time()

        return task

    async def _run_process(
        self,
        task: AsyncTask,
        script_file: Path,
        work_dir: Path,
    ):
        """运行子进程。"""
        env = {**os.environ, "PYSCF_TMPDIR": str(work_dir)}

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(script_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
                env=env,
            )
            task.process = process

            # 并行读取 stdout 和 stderr
            await asyncio.gather(
                self._read_stream(task, process.stdout, "stdout"),
                self._read_stream(task, process.stderr, "stderr"),
            )

            # 等待进程结束
            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.terminate()
                task.status = TaskStatus.FAILED
                task.error_type = "timeout"
                task.error_message = f"计算超时（{self.timeout} 秒）"

            task.return_code = process.returncode
            task.end_time = time.time()

            # 判断状态
            if task.status == TaskStatus.RUNNING:
                if process.returncode == 0:
                    task.status = TaskStatus.COMPLETED
                else:
                    task.status = TaskStatus.FAILED
                    task.error_type, task.error_message = self._classify_error(
                        task.stderr, task.stdout
                    )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_type = "process_error"
            task.error_message = str(e)
            task.end_time = time.time()

    async def _read_stream(
        self,
        task: AsyncTask,
        stream: asyncio.StreamReader,
        stream_name: str,
    ):
        """流式读取输出。"""
        while True:
            try:
                line = await asyncio.wait_for(stream.readline(), timeout=0.1)
                if not line:
                    break

                line_str = line.decode("utf-8", errors="ignore").rstrip()
                if stream_name == "stdout":
                    task.stdout_lines.append(line_str)
                else:
                    task.stderr_lines.append(line_str)

                # 发送进度更新
                await self._emit_progress(task.task_id, line_str)

            except asyncio.TimeoutError:
                # 检查是否被取消
                if task.status == TaskStatus.CANCELLED:
                    break
                continue
            except Exception:
                break

    async def execute_parallel(
        self,
        scripts: list[tuple[str, str]],
    ) -> list[AsyncTask]:
        """
        并行执行多个脚本。

        Parameters
        ----------
        scripts : list[tuple[str, str]]
            [(script, job_name), ...]

        Returns
        -------
        list[AsyncTask]
            任务列表
        """
        tasks = []
        for script, job_name in scripts:
            task = self.execute(script, job_name)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task = AsyncTask(
                    task_id=f"error_{i}",
                    name=scripts[i][1],
                    script=scripts[i][0],
                    status=TaskStatus.FAILED,
                    error_type="gather_error",
                    error_message=str(result),
                )
                results[i] = task

        return results

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
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status != TaskStatus.RUNNING:
            return False

        task.status = TaskStatus.CANCELLED
        if task.process:
            try:
                task.process.terminate()
                # 等待进程退出
                await asyncio.wait_for(task.process.wait(), timeout=5.0)
            except:
                task.process.kill()

        task.end_time = time.time()
        return True

    async def cancel_all(self):
        """取消所有正在运行的任务。"""
        for task_id in list(self._tasks.keys()):
            await self.cancel(task_id)

    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """获取任务。"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[AsyncTask]:
        """获取所有任务。"""
        return list(self._tasks.values())

    def get_running_tasks(self) -> list[AsyncTask]:
        """获取正在运行的任务。"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]

    def _enhance_script(self, script: str) -> str:
        """增强脚本，添加结果提取。"""
        return enhance_script(script)

    def _classify_error(self, stderr: str, stdout: str) -> tuple[str, str]:
        """分类错误。"""
        return classify_error(stderr, stdout)


class AsyncStreamIterator:
    """异步流式迭代器，用于实时输出。"""

    def __init__(self, task: AsyncTask, poll_interval: float = 0.1):
        self.task = task
        self.poll_interval = poll_interval
        self._last_index = 0

    async def __aiter__(self) -> AsyncIterator[str]:
        """异步迭代器。"""
        while True:
            # 检查是否有新行
            while self._last_index < len(self.task.stdout_lines):
                yield self.task.stdout_lines[self._last_index]
                self._last_index += 1

            # 检查任务是否结束
            if self.task.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                # 输出剩余内容
                while self._last_index < len(self.task.stdout_lines):
                    yield self.task.stdout_lines[self._last_index]
                    self._last_index += 1
                break

            await asyncio.sleep(self.poll_interval)


def format_task_status(task: AsyncTask) -> str:
    """格式化任务状态。"""
    status_icons = {
        TaskStatus.PENDING: "[PENDING]",
        TaskStatus.RUNNING: "[RUNNING]",
        TaskStatus.COMPLETED: "[OK]",
        TaskStatus.FAILED: "[FAIL]",
        TaskStatus.CANCELLED: "[CANCELLED]",
    }

    icon = status_icons.get(task.status, "[UNKNOWN]")
    duration = f"{task.duration:.1f}s" if task.duration > 0 else ""

    return f"{icon} [{task.task_id}] {task.name} ({task.status.value}) {duration}"


def format_tasks_table(tasks: list[AsyncTask]) -> str:
    """格式化任务表格。"""
    if not tasks:
        return "没有任务"

    lines = []
    lines.append(f"{'ID':<20} {'名称':<15} {'状态':<12} {'耗时':<10}")
    lines.append("-" * 57)

    for task in tasks:
        duration = f"{task.duration:.1f}s" if task.duration > 0 else "-"
        status = task.status.value
        lines.append(f"{task.task_id:<20} {task.name:<15} {status:<12} {duration:<10}")

    return "\n".join(lines)
