"""Export-only backend — write runnable job package without executing."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from ..executor_common import enhance_script
from ..workdir import create_run_directory
from .base import BackendResult, ExecutionBackend

if TYPE_CHECKING:
    from ...agent import ParsedIntent


def _slurm_script(job_name: str, memory_gb: float, time_hours: float) -> str:
    mem = max(4, int(memory_gb))
    hours = max(1, int(time_hours))
    minutes = hours * 60
    return f"""#!/bin/bash
#SBATCH --job-name={job_name[:20]}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem={mem}G
#SBATCH --time={hours:02d}:00:00
#SBATCH --output={job_name}.slurm.out
#SBATCH --error={job_name}.slurm.err

# 按需加载 Python/PySCF 环境，例如:
# module load anaconda3
# source activate pyscf

cd "${{SLURM_SUBMIT_DIR:-$(dirname "$0")}}"
python {job_name}.py
"""


def _run_shell(job_name: str) -> str:
    return f"""#!/bin/bash
# 本地或远程直接运行（无需 Slurm）
set -euo pipefail
cd "$(dirname "$0")"
python {job_name}.py
"""


def _readme(job_name: str, intent: ParsedIntent, query_text: str) -> str:
    return f"""# Frank 导出任务 — {job_name}

## 内容
- `{job_name}.py` — PySCF 计算脚本
- `run.sh` — 本地直接运行
- `submit.slurm` — Slurm 提交模板
- `manifest.json` — 任务元数据

## 本地运行
```bash
chmod +x run.sh
./run.sh
```

## Slurm 提交
```bash
sbatch submit.slurm
```

## 任务参数
- 分子: {intent.molecule}
- 方法: {intent.method}
- 基组: {intent.basis}
- 计算类型: {intent.calc_type}
- 原始请求: {query_text or '(未记录)'}
"""


class ExportBackend(ExecutionBackend):
    mode_name = "export"

    @property
    def mode(self) -> str:
        return self.mode_name

    def execute(
        self,
        script: str,
        job_name: str,
        intent: ParsedIntent,
        original_basis: Optional[str] = None,
        query_text: str = "",
        estimated_memory_gb: float = 8.0,
        estimated_seconds: float = 3600.0,
    ) -> BackendResult:
        run_dir = create_run_directory(job_name)
        if run_dir is None:
            from pathlib import Path
            import tempfile

            path = Path(tempfile.mkdtemp(prefix="frank_export_"))
            from ..workdir import RunDirectory

            run_dir = RunDirectory(path, job_name)

        enhanced = enhance_script(script)
        py_path = run_dir.write_script(enhanced, f"{job_name}.py")
        slurm_path = run_dir.path / "submit.slurm"
        slurm_path.write_text(
            _slurm_script(job_name, estimated_memory_gb, estimated_seconds / 3600),
            encoding="utf-8",
        )
        run_sh = run_dir.path / "run.sh"
        run_sh.write_text(_run_shell(job_name), encoding="utf-8")
        run_sh.chmod(0o755)

        manifest = {
            "frank_version": "export",
            "created_at": datetime.now().isoformat(),
            "job_name": job_name,
            "query": query_text,
            "intent": {
                "molecule": intent.molecule,
                "method": intent.method,
                "basis": intent.basis,
                "calc_type": intent.calc_type,
                "solvent": intent.solvent,
            },
            "files": {
                "script": py_path.name,
                "slurm": slurm_path.name,
                "run_sh": run_sh.name,
            },
        }
        manifest_path = run_dir.path / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        readme_path = run_dir.path / "README_run.md"
        readme_path.write_text(_readme(job_name, intent, query_text), encoding="utf-8")

        run_dir.write_metadata({"export": True, "mode": "export"})

        export_files = [
            str(py_path),
            str(slurm_path),
            str(run_sh),
            str(manifest_path),
            str(readme_path),
        ]

        return BackendResult(
            mode=self.mode,
            success=True,
            export_dir=str(run_dir.path),
            export_files=export_files,
            message=f"已导出到 {run_dir.path}，可在本机 run.sh 或集群 submit.slurm 运行。",
        )
