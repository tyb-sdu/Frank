import os
import sys
import json
import time
import tempfile
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from .executor_common import enhance_script, classify_error, extract_results_from_stdout
from .workdir import create_run_directory, RunDirectory


@dataclass
class ExecutionResult:
    success: bool
    return_code: int
    stdout: str
    stderr: str
    log_content: str = ""
    duration: float = 0.0
    output_dir: str = ""
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    extracted_results: dict = field(default_factory=dict)

    @property
    def has_output(self) -> bool:
        return bool(self.stdout.strip())

    @property
    def has_error(self) -> bool:
        return bool(self.stderr.strip()) or self.return_code != 0


class PySCFExecutor:
    def __init__(self, work_dir: Optional[str] = None, timeout: int = 600, persist_runs: bool = True, execution_mode: str = "local"):
        self.work_dir = work_dir
        self.timeout = timeout
        self.persist_runs = persist_runs
        self.execution_mode = execution_mode
        self.last_run_dir: Optional[RunDirectory] = None

    def _generate_slurm_script(self, job_name: str, script_name: str) -> str:
        return f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=24:00:00
#SBATCH --output={job_name}_%j.log

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYSCF_MAX_MEMORY=16000

python {script_name}
"""

    def execute(self, script: str, job_name: str = "frank_job") -> ExecutionResult:
        run_dir = None
        if self.work_dir:
            work_dir = Path(self.work_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
        elif self.persist_runs or self.execution_mode == "export":
            run_dir = create_run_directory(job_name)
            if run_dir:
                work_dir = run_dir.path
                self.last_run_dir = run_dir
            else:
                work_dir = Path(tempfile.mkdtemp(prefix="frank_"))
        else:
            work_dir = Path(tempfile.mkdtemp(prefix="frank_"))

        script_file = work_dir / f"{job_name}.py"
        log_file = work_dir / f"{job_name}.log"

        enhanced_script = enhance_script(script)

        try:
            script_file.write_text(enhanced_script, encoding="utf-8")
            if self.execution_mode in ("export", "slurm"):
                slurm_script = work_dir / "submit.slurm"
                slurm_script.write_text(self._generate_slurm_script(job_name, f"{job_name}.py"), encoding="utf-8")
        except OSError as e:
            return ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                output_dir=str(work_dir),
                error_type="file_error",
                error_message=f"无法写入脚本文件: {str(e)}",
            )

        if self.execution_mode == "export":
            msg = f"已成功导出到 {work_dir}。请使用 sbatch submit.slurm 提交作业。"
            exec_result = ExecutionResult(
                success=True,
                return_code=0,
                stdout=msg,
                stderr="",
                log_content="",
                duration=0.0,
                output_dir=str(work_dir),
                error_type=None,
                error_message=None,
                extracted_results={},
            )
            if run_dir:
                run_dir.save_execution(exec_result, {"job_name": job_name, "mode": "export"})
            return exec_result

        if self.execution_mode == "slurm":
            import subprocess
            try:
                res = subprocess.run(["sbatch", "submit.slurm"], cwd=str(work_dir), capture_output=True, text=True, check=True)
                msg = f"已通过 Slurm 提交作业到 {work_dir}。\n{res.stdout}"
            except Exception as e:
                msg = f"已导出到 {work_dir}，但自动提交 sbatch 失败 (可能是当前环境没有 slurm)。\n错误信息: {e}"
            
            exec_result = ExecutionResult(
                success=True,
                return_code=0,
                stdout=msg,
                stderr="",
                log_content="",
                duration=0.0,
                output_dir=str(work_dir),
                error_type=None,
                error_message=None,
                extracted_results={},
            )
            if run_dir:
                run_dir.save_execution(exec_result, {"job_name": job_name, "mode": "slurm"})
            return exec_result

        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, str(script_file)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(work_dir),
                env={**os.environ, "PYSCF_TMPDIR": str(work_dir)},
            )
            duration = time.time() - start_time

            log_content = ""
            if log_file.exists():
                try:
                    log_content = log_file.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

            extracted = extract_results_from_stdout(result.stdout)

            success = result.returncode == 0
            error_type = None
            error_message = None

            if not success:
                error_type, error_message, _ = classify_error(result.stderr, result.stdout)

            exec_result = ExecutionResult(
                success=success,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                log_content=log_content,
                duration=duration,
                output_dir=str(work_dir),
                error_type=error_type,
                error_message=error_message,
                extracted_results=extracted,
            )
            if run_dir:
                run_dir.save_execution(exec_result, {"job_name": job_name})
            return exec_result

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"执行超时（超过 {self.timeout} 秒）",
                duration=duration,
                output_dir=str(work_dir),
                error_type="timeout",
                error_message=f"计算超时（{self.timeout} 秒），可能需要增加 timeout 或简化计算",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                output_dir=str(work_dir),
                error_type="executor_error",
                error_message=f"执行器错误: {str(e)}",
            )

    def execute_with_recovery(
        self,
        script: str,
        job_name: str = "frank_job",
        original_basis: str = None,
    ) -> tuple[ExecutionResult, list[str]]:
        from .recovery import (
            get_recovery_strategies,
            prepare_retry_script,
        )

        result = self.execute(script, job_name)
        if result.success:
            return result, []

        error_type = result.error_type
        if not error_type:
            return result, []

        strategies = get_recovery_strategies(error_type)
        if not strategies:
            return result, []

        retry_log = []
        for i, strategy in enumerate(strategies):
            log_entry = f"Retry {i+1}/{len(strategies)}: {strategy.description}"
            retry_log.append(log_entry)

            retry_script = prepare_retry_script(
                script, error_type, strategy, original_basis
            )

            retry_name = f"{job_name}_retry{i+1}"
            result = self.execute(retry_script, retry_name)

            if result.success:
                retry_log.append(f"[OK] Retry {i+1} succeeded (strategy: {strategy.strategy})")
                return result, retry_log
            else:
                retry_log.append(f"[FAIL] Retry {i+1} failed: {result.error_type}")

        retry_log.append("[WARN] All recovery strategies exhausted; calculation failed")
        return result, retry_log


def save_execution_result(result: ExecutionResult, output_file: str):
    data = {
        "success": result.success,
        "return_code": result.return_code,
        "duration": result.duration,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error_type": result.error_type,
        "error_message": result.error_message,
        "output_dir": result.output_dir,
        "extracted_results": result.extracted_results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
